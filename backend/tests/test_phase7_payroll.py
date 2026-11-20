"""
Phase 7 - Payroll and time: pay schedules, pay items, employees, payroll
runs, paychecks, liabilities, pay stubs, time tracking and billable time.
"""

import pytest

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer

PERIOD_END = "2026-11-20"
PAY_DATE = "2026-11-25"


def post(client, path, payload, expected=201):
    response = client.post(f"{API}{path}", json=payload)
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture
def payroll(auth_client):
    schedule = post(
        auth_client,
        "/pay-schedules",
        {"name": "Every other Friday", "frequency": "BIWEEKLY", "next_period_end": PERIOD_END, "next_pay_date": PAY_DATE},
    )
    pension = post(auth_client, "/pay-items", {"name": "401(k)", "kind": "DEDUCTION", "calculation": "PERCENT", "default_amount": "5"})
    income_tax = post(
        auth_client, "/pay-items", {"name": "Federal income tax", "kind": "EMPLOYEE_TAX", "calculation": "PERCENT", "default_amount": "10"}
    )
    social = post(
        auth_client, "/pay-items", {"name": "Employer social security", "kind": "EMPLOYER_TAX", "calculation": "PERCENT", "default_amount": "6.2"}
    )
    bonus = post(auth_client, "/pay-items", {"name": "Bonus", "kind": "EARNING", "calculation": "FIXED"})

    hourly = post(
        auth_client,
        "/employees",
        {
            "display_name": "Hannah Hourly",
            "pay_schedule_id": schedule["id"],
            "pay_type": "HOURLY",
            "pay_rate": "20",
            "default_hours": "80",
            "pay_items": [
                {"pay_item_id": pension["id"], "amount": "5"},
                {"pay_item_id": income_tax["id"], "amount": "10"},
                {"pay_item_id": social["id"], "amount": "6.2"},
            ],
        },
    )
    salaried = post(
        auth_client,
        "/employees",
        {
            "display_name": "Sam Salary",
            "pay_schedule_id": schedule["id"],
            "pay_type": "SALARY",
            "pay_rate": "52000",
            "payment_method": "DIRECT_DEPOSIT",
            "pay_items": [{"pay_item_id": income_tax["id"], "amount": "10"}],
        },
    )
    # Hannah logged 70 hours in the period (Nov 7 - Nov 20).
    post(auth_client, "/time-entries", {"employee_id": hourly["id"], "work_date": "2026-11-09", "hours": "8"})
    for day in range(10, 20):
        post(auth_client, "/time-entries", {"employee_id": hourly["id"], "work_date": f"2026-11-{day}", "hours": "6.2"})
    return {
        "schedule": schedule,
        "pension": pension,
        "income_tax": income_tax,
        "social": social,
        "bonus": bonus,
        "hourly": hourly,
        "salaried": salaried,
        "bank": account_id(auth_client, "Checking"),
    }


def create_run(client, setup):
    return post(client, "/payroll-runs", {"pay_schedule_id": setup["schedule"]["id"], "bank_account_id": setup["bank"]})


def paycheck_of(run, employee_id):
    for paycheck in run["paychecks"]:
        if paycheck["employee"]["id"] == employee_id:
            return paycheck
    raise AssertionError(employee_id)


def test_draft_paychecks(auth_client, payroll):
    run = create_run(auth_client, payroll)
    assert run["status"] == "DRAFT"
    assert run["period_start"] == "2026-11-07"
    assert run["pay_date"] == PAY_DATE

    hannah = paycheck_of(run, payroll["hourly"]["id"])
    assert float(hannah["regular_hours"]) == 70  # from her time entries
    assert float(hannah["gross_pay"]) == 1400
    assert float(hannah["employee_deductions"]) == 70  # 5%
    assert float(hannah["employee_taxes"]) == 140  # 10%
    assert float(hannah["employer_cost"]) == 86.8  # 6.2%
    assert float(hannah["net_pay"]) == 1190

    sam = paycheck_of(run, payroll["salaried"]["id"])
    assert float(sam["gross_pay"]) == 2000  # 52,000 / 26
    assert float(sam["net_pay"]) == 1800

    # Nothing is posted until the payroll is approved.
    assert balance_of(auth_client, "Wages & Salaries") == 0


def test_edit_approve_and_liabilities(auth_client, payroll):
    run = create_run(auth_client, payroll)
    hannah = paycheck_of(run, payroll["hourly"]["id"])
    edited = auth_client.put(
        f"{API}/payroll-runs/{run['id']}/paychecks/{hannah['id']}",
        json={
            "regular_hours": "70",
            "overtime_hours": "5",
            "items": [
                {"pay_item_id": payroll["bonus"]["id"], "amount": "50"},
                {"pay_item_id": payroll["pension"]["id"], "amount": "80"},
                {"pay_item_id": payroll["income_tax"]["id"], "amount": "160"},
                {"pay_item_id": payroll["social"]["id"], "amount": "99.20"},
            ],
        },
    )
    assert edited.status_code == 200, edited.text
    hannah = paycheck_of(edited.json(), payroll["hourly"]["id"])
    assert float(hannah["gross_pay"]) == 1400 + 150 + 50  # overtime 5 x 30, bonus 50
    assert float(hannah["net_pay"]) == 1600 - 80 - 160

    approved = auth_client.post(f"{API}/payroll-runs/{run['id']}/approve")
    assert approved.status_code == 200, approved.text
    approved = approved.json()
    assert approved["status"] == "APPROVED"
    assert paycheck_of(approved, payroll["hourly"]["id"])["check_number"] is not None
    assert paycheck_of(approved, payroll["salaried"]["id"])["check_number"] is None  # direct deposit

    assert balance_of(auth_client, "Wages & Salaries") == 3600  # 1600 + 2000
    assert balance_of(auth_client, "Payroll Taxes & Benefits") == 99.2
    assert balance_of(auth_client, "Payroll Liabilities") == 80 + 160 + 99.2 + 200
    assert balance_of(auth_client, "Checking") == -(1360 + 1800)
    assert_books_balance(auth_client)

    schedule = auth_client.get(f"{API}/pay-schedules").json()[0]
    assert schedule["next_period_end"] == "2026-12-04"
    assert schedule["next_pay_date"] == "2026-12-09"

    locked = auth_client.put(f"{API}/payroll-runs/{run['id']}/paychecks/{hannah['id']}", json={"regular_hours": "1"})
    assert locked.status_code == 422

    balances = {row["name"]: row for row in auth_client.get(f"{API}/payroll-liabilities").json()}
    assert float(balances["Federal income tax"]["balance"]) == 360

    too_much = auth_client.post(
        f"{API}/payroll-liabilities/payments",
        json={"pay_item_id": payroll["income_tax"]["id"], "payment_date": TODAY, "amount": "400", "bank_account_id": payroll["bank"]},
    )
    assert too_much.status_code == 422
    post(
        auth_client,
        "/payroll-liabilities/payments",
        {"pay_item_id": payroll["income_tax"]["id"], "payment_date": TODAY, "amount": "360", "bank_account_id": payroll["bank"]},
    )
    balances = {row["name"]: row for row in auth_client.get(f"{API}/payroll-liabilities").json()}
    assert float(balances["Federal income tax"]["balance"]) == 0
    assert balance_of(auth_client, "Payroll Liabilities") == 179.2

    stub = auth_client.get(f"{API}/payroll-runs/{run['id']}/paychecks/{hannah['id']}/stub")
    assert stub.status_code == 200
    assert stub.headers["content-type"] == "application/pdf"

    report = auth_client.get(f"{API}/reports/payroll-summary?start_date=2026-11-01&end_date=2026-11-30").json()
    summary = {row["label"]: row["amount"] for row in report["summary"]}
    assert summary["Total gross pay"] == "3600.00"
    assert summary["Total net pay"] == "3160.00"
    assert summary["Total payroll cost"] == "3699.20"

    voided = auth_client.post(f"{API}/payroll-runs/{run['id']}/void")
    assert voided.status_code == 200
    assert balance_of(auth_client, "Wages & Salaries") == 0
    assert_books_balance(auth_client)


def test_hours_change_recalculates_usual_items(auth_client, payroll):
    run = create_run(auth_client, payroll)
    hannah = paycheck_of(run, payroll["hourly"]["id"])
    updated = auth_client.put(
        f"{API}/payroll-runs/{run['id']}/paychecks/{hannah['id']}",
        json={"regular_hours": "80", "use_usual_items": True},
    ).json()
    hannah = paycheck_of(updated, payroll["hourly"]["id"])
    assert float(hannah["gross_pay"]) == 1600
    assert float(hannah["employee_taxes"]) == 160  # 10% of the new gross
    assert float(hannah["employee_deductions"]) == 80


def test_draft_rules(auth_client, payroll):
    run = create_run(auth_client, payroll)
    assert auth_client.post(f"{API}/payroll-runs/{run['id']}/void").status_code == 422
    assert auth_client.delete(f"{API}/payroll-runs/{run['id']}").status_code == 204
    assert auth_client.get(f"{API}/payroll-runs").json() == []

    too_big = post(auth_client, "/pay-items", {"name": "Garnishment", "kind": "DEDUCTION", "calculation": "FIXED"})
    run = create_run(auth_client, payroll)
    sam = paycheck_of(run, payroll["salaried"]["id"])
    negative = auth_client.put(
        f"{API}/payroll-runs/{run['id']}/paychecks/{sam['id']}",
        json={"items": [{"pay_item_id": too_big["id"], "amount": "5000"}]},
    )
    assert negative.status_code == 422

    builtin = auth_client.post(f"{API}/pay-items", json={"name": "Regular", "kind": "REGULAR"})
    assert builtin.status_code == 422


def test_billable_time_on_invoice(auth_client, payroll):
    customer = make_customer(auth_client)
    service = auth_client.post(f"{API}/products", json={"name": "Garden labour", "sales_price": "45"}).json()
    entry = post(
        auth_client,
        "/time-entries",
        {
            "employee_id": payroll["hourly"]["id"],
            "work_date": TODAY,
            "hours": "2",
            "customer_id": customer,
            "product_id": service["id"],
            "billable": True,
            "description": "Pruning",
        },
    )
    assert float(entry["bill_rate"]) == 45  # from the service's price

    unbilled = auth_client.get(f"{API}/time-entries?customer_id={customer}&unbilled_only=true").json()
    assert [row["id"] for row in unbilled] == [entry["id"]]

    invoice = post(auth_client, "/invoices", {"customer_id": customer, "invoice_date": TODAY, "time_entry_ids": [entry["id"]]})
    assert float(invoice["total"]) == 90
    assert "Hannah Hourly: Pruning" in invoice["lines"][0]["description"]
    assert auth_client.get(f"{API}/time-entries?customer_id={customer}&unbilled_only=true").json() == []

    again = auth_client.post(f"{API}/invoices", json={"customer_id": customer, "invoice_date": TODAY, "time_entry_ids": [entry["id"]]})
    assert again.status_code == 422
    assert auth_client.delete(f"{API}/time-entries/{entry['id']}").status_code == 422

    auth_client.post(f"{API}/invoices/{invoice['id']}/void")
    assert len(auth_client.get(f"{API}/time-entries?customer_id={customer}&unbilled_only=true").json()) == 1

    nobody = auth_client.post(f"{API}/time-entries", json={"work_date": TODAY, "hours": "1"})
    assert nobody.status_code == 422
    no_customer = auth_client.post(
        f"{API}/time-entries", json={"employee_id": payroll["hourly"]["id"], "work_date": TODAY, "hours": "1", "billable": True}
    )
    assert no_customer.status_code == 422


def test_provider_is_behind_an_interface(auth_client):
    assert auth_client.get(f"{API}/payroll/provider").json() == {"enabled": False, "provider": "none"}
