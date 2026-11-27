"""Cash-flow forecast: every source lands on the right day with the right amount."""

from datetime import date, timedelta

from app.core.config import settings
from tests.test_payment_score import invoice_paid_late
from tests.test_phase2_sales import API, account_id, make_customer, make_invoice

TODAY = date.today()


def ahead(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


def post(client, path, body):
    response = client.post(f"{API}{path}", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def forecast(client):
    response = client.get(f"{API}/forecast")
    assert response.status_code == 200, response.text
    return response.json()


def rows(data, kind):
    return [(item["date"], float(item["amount"])) for item in data["items"] if item["type"] == kind]


def balance_on(data, on: str) -> float:
    return float([day for day in data["days"] if day["date"] == on][0]["balance"])


def make_vendor(client, name="Power Co"):
    return post(client, "/vendors", {"display_name": name})["id"]


def make_bill(client, vendor_id, amount, due_in: int):
    line = {"account_id": account_id(client, "Insurance"), "rate": str(amount)}
    return post(
        client,
        "/purchase-documents",
        {"doc_type": "BILL", "vendor_id": vendor_id, "doc_date": TODAY.isoformat(), "due_date": ahead(due_in), "lines": [line]},
    )


def schedule(client, name, kind, template, start_in: int, frequency="MONTHLY"):
    body = {"name": name, "transaction_type": kind, "frequency": frequency, "start_date": ahead(start_in), "template": template}
    return post(client, "/recurring", body)


def test_empty_books_give_a_flat_forecast(auth_client):
    data = forecast(auth_client)
    assert data["items"] == [] and data["first_low_date"] is None and data["notes"] == []
    assert len(data["days"]) == settings.forecast_days + 1
    assert float(data["starting_balance"]) == 0


def test_invoices_and_bills(auth_client):
    late_payer = make_customer(auth_client, "Late Payer")
    for _ in range(3):
        invoice_paid_late(auth_client, late_payer, 10)  # money goes to Undeposited Funds
    on_time = make_customer(auth_client, "On Time")

    make_invoice(auth_client, late_payer, rate=500, due_date=ahead(5))  # expected 10 days later
    make_invoice(auth_client, on_time, rate=200, due_date=ahead(7))
    make_invoice(auth_client, on_time, rate=50, invoice_date=ahead(-20), due_date=ahead(-3))  # overdue -> today
    make_invoice(auth_client, on_time, rate=999, due_date=ahead(settings.forecast_days + 1))  # too far away
    vendor = make_vendor(auth_client)
    make_bill(auth_client, vendor, 900, due_in=2)

    data = forecast(auth_client)
    assert rows(data, "Invoice") == [(ahead(0), 50.0), (ahead(7), 200.0), (ahead(15), 500.0)]
    assert rows(data, "Bill") == [(ahead(2), -900.0)]
    assert rows(data, "Deposit") == [(ahead(0), 300.0)]
    assert balance_on(data, ahead(0)) == 350
    assert balance_on(data, ahead(2)) == -550
    assert balance_on(data, ahead(15)) == 150
    assert data["first_low_date"] == ahead(2) and float(data["lowest"]["balance"]) == -550


def test_recurring_transactions(auth_client):
    customer = make_customer(auth_client)
    vendor = make_vendor(auth_client)
    checking = account_id(auth_client, "Checking")
    supplies = account_id(auth_client, "Insurance")

    work = {"description": "Retainer", "quantity": "1", "rate": "1000"}
    schedule(auth_client, "Retainer", "INVOICE", {"customer_id": customer, "lines": [work], "discount_type": "PERCENT", "discount_value": "10"}, 1)
    schedule(auth_client, "Till", "SALES_RECEIPT", {"customer_id": customer, "lines": [{**work, "rate": "40"}]}, 3)
    expense = {"payment_account_id": checking, "payment_method": "BANK_TRANSFER", "lines": [{"account_id": supplies, "amount": "300"}]}
    schedule(auth_client, "Rent", "EXPENSE", expense, 4)
    bill = {"vendor_id": vendor, "lines": [{"account_id": supplies, "rate": "70"}]}
    schedule(auth_client, "Internet", "BILL", bill, 5)
    equity = account_id(auth_client, "Owner's Investment")
    entry = {"lines": [{"account_id": checking, "debit": "25"}, {"account_id": equity, "credit": "25"}]}
    schedule(auth_client, "Top up", "JOURNAL_ENTRY", entry, 6)

    data = forecast(auth_client)
    assert data["notes"] == []
    recurring = [(item["description"], item["date"], float(item["amount"])) for item in data["items"] if item["type"] == "Recurring"]
    firsts = {}
    for name, on, amount in recurring:
        firsts.setdefault(name, (on, amount))
    # Invoices and bills move money on their due date (30 days by default).
    assert firsts == {
        "Retainer": (ahead(31), 900.0),
        "Till": (ahead(3), 40.0),
        "Rent": (ahead(4), -300.0),
        "Internet": (ahead(35), -70.0),
        "Top up": (ahead(6), 25.0),
    }
    assert len([row for row in recurring if row[0] == "Rent"]) == 3  # monthly for 90 days


def test_payroll_pay_days(auth_client):
    pay_schedule = post(
        auth_client, "/pay-schedules", {"name": "Fortnightly", "frequency": "BIWEEKLY", "next_period_end": ahead(5), "next_pay_date": ahead(7)}
    )
    post(
        auth_client,
        "/employees",
        {"display_name": "Sam", "pay_schedule_id": pay_schedule["id"], "pay_type": "SALARY", "pay_rate": "52000", "payment_method": "CHECK"},
    )
    pay_rows = rows(forecast(auth_client), "Payroll")
    assert pay_rows[:2] == [(ahead(7), -2000.0), (ahead(21), -2000.0)]
    assert len(pay_rows) == 6  # days 7, 21, 35, 49, 63, 77

    # A draft payroll replaces the estimate for its period: it is not counted twice.
    post(auth_client, "/payroll-runs", {"pay_schedule_id": pay_schedule["id"], "bank_account_id": account_id(auth_client, "Checking")})
    data = forecast(auth_client)
    assert rows(data, "Payroll") == pay_rows
    assert data["items"][0]["description"] == "Draft payroll"


def test_forecast_needs_report_access_and_stays_inside_the_company(auth_client):
    customer = make_customer(auth_client)
    make_invoice(auth_client, customer, rate=100, due_date=ahead(3))
    other = auth_client.post(
        f"{API}/auth/signup",
        json={"full_name": "Other", "company_name": "Other Co", "email": "other@example.com", "password": "secret-password"},
    ).json()["access_token"]
    assert auth_client.get(f"{API}/forecast", headers={"Authorization": f"Bearer {other}"}).json()["items"] == []
