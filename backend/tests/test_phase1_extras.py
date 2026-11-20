"""
Sub-accounts and recurring journal entries.
"""

from datetime import date

from app.core.dates import add_months
from app.models import RecurringSchedule
from app.models.enums import RecurringFrequency
from app.services.recurring_service import occurrence_date

API = "/api/v1"


def account_id(client, name):
    for account in client.get(f"{API}/accounts").json():
        if account["name"] == name:
            return account["id"]
    raise AssertionError(name)


# ---------- sub-accounts ----------

def test_sub_account_is_listed_under_its_parent(auth_client):
    utilities = account_id(auth_client, "Utilities")
    response = auth_client.post(
        f"{API}/accounts",
        json={"name": "Electric", "account_type": "EXPENSE", "detail_type": "Utilities", "parent_id": utilities},
    )
    assert response.status_code == 201, response.text

    accounts = auth_client.get(f"{API}/accounts").json()
    names = [account["full_name"] for account in accounts]
    assert names.index("Utilities:Electric") == names.index("Utilities") + 1
    electric = accounts[names.index("Utilities:Electric")]
    assert electric["depth"] == 1


def test_sub_account_must_match_parent_type(auth_client):
    response = auth_client.post(
        f"{API}/accounts",
        json={"name": "Wrong", "account_type": "INCOME", "detail_type": "x", "parent_id": account_id(auth_client, "Utilities")},
    )
    assert response.status_code == 422


def test_sub_account_loops_are_blocked(auth_client):
    utilities = account_id(auth_client, "Utilities")
    child = auth_client.post(
        f"{API}/accounts",
        json={"name": "Water", "account_type": "EXPENSE", "detail_type": "Utilities", "parent_id": utilities},
    ).json()
    # Try to make Utilities a sub-account of its own child.
    response = auth_client.put(
        f"{API}/accounts/{utilities}",
        json={"name": "Utilities", "detail_type": "Utilities", "parent_id": child["id"]},
    )
    assert response.status_code == 422


# ---------- recurring dates ----------

def test_month_end_dates_do_not_drift():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    schedule = RecurringSchedule(start_date=date(2026, 1, 31), frequency=RecurringFrequency.MONTHLY, interval=1)
    assert occurrence_date(schedule, 1) == date(2026, 2, 28)
    assert occurrence_date(schedule, 2) == date(2026, 3, 31)


# ---------- recurring journal entries ----------

def recurring_rent_payload(client, start_date, end_date=None):
    return {
        "name": "Monthly depreciation",
        "transaction_type": "JOURNAL_ENTRY",
        "frequency": "MONTHLY",
        "interval": 1,
        "start_date": start_date,
        "end_date": end_date,
        "template": {
            "memo": "Depreciation",
            "lines": [
                {"account_id": account_id(client, "Repairs & Maintenance"), "debit": "100"},
                {"account_id": account_id(client, "Furniture and Equipment"), "credit": "100"},
            ],
        },
    }


def test_recurring_journal_creates_every_missed_month(auth_client):
    response = auth_client.post(f"{API}/recurring", json=recurring_rent_payload(auth_client, "2026-01-15", "2026-03-31"))
    assert response.status_code == 201, response.text
    assert response.json()["next_date"] == "2026-01-15"

    result = auth_client.post(f"{API}/recurring/run-due").json()
    dates = [item["transaction_date"] for item in result["created"]]
    assert dates == ["2026-01-15", "2026-02-15", "2026-03-15"]

    schedule = auth_client.get(f"{API}/recurring/{response.json()['id']}").json()
    assert schedule["run_count"] == 3
    assert schedule["next_date"] is None  # ended

    # Running again creates nothing.
    assert auth_client.post(f"{API}/recurring/run-due").json()["created"] == []

    report = auth_client.get(f"{API}/reports/profit-and-loss?start_date=2026-01-01&end_date=2026-12-31").json()
    assert float(report["summary"][-1]["amount"]) == -300


def test_unbalanced_recurring_template_is_rejected(auth_client):
    payload = recurring_rent_payload(auth_client, "2026-01-01")
    payload["template"]["lines"][1]["credit"] = "90"
    response = auth_client.post(f"{API}/recurring", json=payload)
    assert response.status_code == 422


def test_future_schedule_does_not_run_yet(auth_client):
    auth_client.post(f"{API}/recurring", json=recurring_rent_payload(auth_client, "2099-01-01"))
    assert auth_client.post(f"{API}/recurring/run-due").json()["created"] == []
