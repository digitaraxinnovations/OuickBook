"""Books health check: each check finds its planted problem and stays quiet on clean books."""

import base64
from datetime import date, timedelta

from app.core.config import settings
from tests.test_phase2_sales import API, account_id, make_customer, make_invoice

TODAY = date.today()


def ago(days: int) -> str:
    return (TODAY - timedelta(days=days)).isoformat()


def post(client, path, body, status=201):
    response = client.post(f"{API}{path}", json=body)
    assert response.status_code == status, response.text
    return response.json() if response.content else None


def report(client):
    response = client.get(f"{API}/health-check")
    assert response.status_code == 200, response.text
    return response.json()


def checks_found(data):
    return sorted(finding["check"] for finding in data["findings"] if not finding["dismissed"])


def make_vendor(client, name="Power Co"):
    return post(client, "/vendors", {"display_name": name})["id"]


def make_expense(client, vendor_id, amount, days_ago=1, category="Insurance"):
    return post(
        client,
        "/expenses",
        {
            "vendor_id": vendor_id,
            "payment_account_id": account_id(client, "Checking"),
            "expense_date": ago(days_ago),
            "payment_method": "BANK_TRANSFER",
            "lines": [{"account_id": account_id(client, category), "amount": str(amount)}],
        },
    )["id"]


def attach_receipt(client, expense_id):
    body = {
        "entity_type": "EXPENSE",
        "entity_id": expense_id,
        "filename": "receipt.txt",
        "mime_type": "text/plain",
        "data_base64": base64.b64encode(b"paid").decode(),
    }
    post(client, "/attachments", body)


def test_clean_books_score_100(auth_client):
    vendor = make_vendor(auth_client)
    make_expense(auth_client, vendor, 50)  # under the receipt limit
    assert report(auth_client) == {"score": 100, "findings": []}


def test_duplicates_unusual_amounts_and_missing_receipts(auth_client):
    vendor = make_vendor(auth_client)
    for days_ago in (90, 60, 30):
        make_expense(auth_client, vendor, 60, days_ago)
    first = make_expense(auth_client, vendor, 70, days_ago=20)
    make_expense(auth_client, vendor, 70, days_ago=20 - settings.health_duplicate_days)
    big = make_expense(auth_client, vendor, 400, days_ago=2)

    data = report(auth_client)
    # The 90-day-old spending also means Checking is overdue for reconciliation.
    assert checks_found(data) == ["Missing receipts", "Possible duplicates", "Reconciliation", "Unusual amounts"]
    assert data["score"] == 100 - 10 - 5 - 5 - 2
    assert [f["severity"] for f in data["findings"]] == ["HIGH", "MEDIUM", "MEDIUM", "LOW"]  # most important first
    unusual = [f for f in data["findings"] if f["check"] == "Unusual amounts"][0]
    assert unusual["link"] == f"/expenses/{big}"
    assert f"expense{first}" in [f for f in data["findings"] if f["check"] == "Possible duplicates"][0]["key"]

    attach_receipt(auth_client, big)
    assert "Missing receipts" not in checks_found(report(auth_client))


def test_this_is_fine_is_remembered_and_can_be_undone(auth_client):
    vendor = make_vendor(auth_client)
    make_expense(auth_client, vendor, 70)
    make_expense(auth_client, vendor, 70)
    key = report(auth_client)["findings"][0]["key"]

    post(auth_client, "/health-check/dismissals", {"key": key}, status=204)
    post(auth_client, "/health-check/dismissals", {"key": key}, status=204)  # twice is harmless
    data = report(auth_client)
    assert data["score"] == 100 and data["findings"][0]["dismissed"] is True

    assert auth_client.delete(f"{API}/health-check/dismissals", params={"key": key}).status_code == 204
    assert report(auth_client)["score"] == 90


def test_money_owed_and_bookkeeping_checks(auth_client):
    customer = make_customer(auth_client)
    make_invoice(auth_client, customer, invoice_date=ago(130), due_date=ago(100))
    make_invoice(auth_client, customer, invoice_date=ago(100), due_date=ago(90))  # exactly 90 days: not yet
    paid = make_invoice(auth_client, customer, invoice_date=ago(40), due_date=ago(30))
    post(  # an overpayment, received 20 days ago and never deposited
        auth_client,
        "/payments",
        {"customer_id": customer, "payment_date": ago(20), "amount": "150", "applications": [{"invoice_id": paid["id"], "amount": "100"}]},
    )
    vendor = make_vendor(auth_client)
    make_expense(auth_client, vendor, 30, days_ago=60, category="Uncategorized Expense")  # old bank activity too

    assert checks_found(report(auth_client)) == [
        "Old unpaid invoices",
        "Reconciliation",
        "Uncategorized",
        "Undeposited money",
        "Unused credits",
    ]


def test_bank_lines_waiting_for_review(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "bank_feed_provider", "mock")
    checking = account_id(auth_client, "Checking")
    assert auth_client.post(f"{API}/banking/accounts/{checking}/sync").status_code == 200
    assert checks_found(report(auth_client)) == ["Bank lines to review"]


def test_one_busy_check_cannot_zero_the_score(auth_client):
    customer = make_customer(auth_client)
    for _ in range(6):
        make_invoice(auth_client, customer, invoice_date=ago(130), due_date=ago(100))
    assert report(auth_client)["score"] == 100 - settings.health_max_points_per_check


def test_findings_stay_inside_the_company(auth_client):
    vendor = make_vendor(auth_client)
    make_expense(auth_client, vendor, 500)
    other = auth_client.post(
        f"{API}/auth/signup",
        json={"full_name": "Other", "company_name": "Other Co", "email": "other@example.com", "password": "secret-password"},
    ).json()["access_token"]
    data = auth_client.get(f"{API}/health-check", headers={"Authorization": f"Bearer {other}"}).json()
    assert data == {"score": 100, "findings": []}
