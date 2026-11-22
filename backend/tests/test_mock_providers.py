"""
The built-in mock providers for the four outside services (payments, bank feed,
sales tax, payroll). They work like the real thing but nothing real happens.
The `providers_off` fixture in conftest.py turns every provider off, so each
test here switches on the one it needs.
"""

from datetime import date

from app.core.config import settings
from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer
from tests.test_phase5_taxes import JULY, YEAR, setup_taxes, taxed_invoice
from tests.test_phase7_payroll import PAY_DATE, create_run, paycheck_of, payroll, post  # noqa: F401  (payroll is a fixture)


# ------------------------------------------------------------------ payments
def test_simulated_checkout_records_a_payment(auth_client, monkeypatch):
    customer = make_customer(auth_client, "Pays Online")
    invoice = auth_client.post(
        f"{API}/invoices", json={"customer_id": customer, "invoice_date": TODAY, "lines": [{"description": "Work", "quantity": "1", "rate": "100"}]}
    ).json()
    token = auth_client.post(f"{API}/invoices/{invoice['id']}/share-link").json()["url"].rsplit("/", 1)[1]
    login = auth_client.headers.pop("Authorization")

    # Provider off: no Pay now button, and the simulated route refuses.
    assert auth_client.get(f"{API}/public/invoices/{token}").json()["online_payment_enabled"] is False
    assert auth_client.post(f"{API}/public/invoices/{token}/mock-pay", json={}).status_code == 422

    monkeypatch.setattr(settings, "payment_provider", "mock")
    page = auth_client.get(f"{API}/public/invoices/{token}").json()
    assert page["online_payment_enabled"] is True and page["online_payment_simulated"] is True
    checkout = auth_client.post(f"{API}/public/invoices/{token}/pay", json={}).json()["checkout_url"]
    assert f"/portal/mock-checkout/{token}" in checkout

    assert float(auth_client.post(f"{API}/public/invoices/{token}/mock-pay", json={"amount": "40"}).json()["amount_paid"]) == 40
    paid = auth_client.post(f"{API}/public/invoices/{token}/mock-pay", json={}).json()
    assert float(paid["balance_due"]) == 0 and paid["status"] == "PAID"
    assert auth_client.post(f"{API}/public/invoices/{token}/mock-pay", json={}).status_code == 422  # already paid

    auth_client.headers["Authorization"] = login
    assert balance_of(auth_client, "Undeposited Funds") == 100
    assert_books_balance(auth_client)


# ------------------------------------------------------------------ bank feed
def test_simulated_bank_feed(auth_client, monkeypatch):
    checking = account_id(auth_client, "Checking")
    assert auth_client.post(f"{API}/banking/accounts/{checking}/sync").status_code == 422  # provider off

    monkeypatch.setattr(settings, "bank_feed_provider", "mock")
    first = auth_client.post(f"{API}/banking/accounts/{checking}/sync").json()
    assert first["imported"] == settings.mock_bank_feed_days * 2 and first["duplicates"] == 0

    again = auth_client.post(f"{API}/banking/accounts/{checking}/sync").json()
    assert again["imported"] == 0 and again["duplicates"] == first["imported"]  # the same lines are not added twice


# ------------------------------------------------------------------ sales tax
def test_simulated_tax_lookup_and_e_filing(auth_client, monkeypatch):
    taxes = setup_taxes(auth_client)
    assert auth_client.post(f"{API}/taxes/lookup", json={"address": "1 Main St, Springfield, IL 62701"}).status_code == 422  # provider off

    monkeypatch.setattr(settings, "tax_rate_provider", "mock")
    assert auth_client.get(f"{API}/taxes/lookup/status").json() == {"enabled": True, "provider": "mock"}
    found = auth_client.post(f"{API}/taxes/lookup", json={"address": "120 Maple Street, Springfield, IL 62701"}).json()
    assert [item["name"] for item in found] == ["Illinois state tax", "Local tax 62701"]
    assert float(found[0]["rate"]) == 6.25
    unknown = auth_client.post(f"{API}/taxes/lookup", json={"address": "somewhere unknown"}).json()
    assert float(unknown[0]["rate"]) == float(settings.mock_tax_default_rate)

    customer = make_customer(auth_client)
    taxed_invoice(auth_client, customer, taxes["code"]["id"], invoice_date=JULY)  # 72.50 tax in a finished quarter
    request = {
        "agency_id": taxes["agency_id"],
        "period_start": f"{YEAR}-07-01",
        "period_end": f"{YEAR}-09-30",
        "payment_date": TODAY,
        "payment_account_id": account_id(auth_client, "Checking"),
    }
    filed = auth_client.post(f"{API}/taxes/file-return", json=request)
    assert filed.status_code == 201, filed.text
    assert filed.json()["confirmation_no"].startswith("MOCK-EF-") and float(filed.json()["amount"]) == 72.50

    periods = auth_client.get(f"{API}/taxes/periods?agency_id={taxes['agency_id']}").json()
    q3 = [p for p in periods if p["period_start"] == f"{YEAR}-07-01"][0]
    assert q3["status"] == "PAID"
    assert auth_client.post(f"{API}/taxes/file-return", json=request).status_code == 422  # nothing left to file

    current = {**request, "period_start": f"{YEAR}-10-01", "period_end": f"{YEAR}-12-31"}
    assert auth_client.post(f"{API}/taxes/file-return", json=current).status_code == 422  # this quarter is not over
    assert_books_balance(auth_client)


# ------------------------------------------------------------------ payroll
def test_simulated_payroll_taxes_and_direct_deposit(auth_client, payroll, monkeypatch):  # noqa: F811
    assert auth_client.get(f"{API}/payroll/provider").json() == {"enabled": False, "provider": "none"}
    monkeypatch.setattr(settings, "payroll_provider", "mock")
    assert auth_client.get(f"{API}/payroll/provider").json() == {"enabled": True, "provider": "mock"}

    # An employee with no taxes set up by hand gets the provider's taxes.
    alex = post(
        auth_client,
        "/employees",
        {"display_name": "Auto Alex", "pay_schedule_id": payroll["schedule"]["id"], "pay_type": "SALARY", "pay_rate": "52000", "payment_method": "DIRECT_DEPOSIT"},
    )
    run = create_run(auth_client, payroll)
    auto = paycheck_of(run, alex["id"])
    assert float(auto["gross_pay"]) == 2000
    assert float(auto["employee_taxes"]) == 353.00  # 10% federal + 6.2% social security + 1.45% medicare
    assert float(auto["employer_cost"]) == 153.00  # 6.2% + 1.45%
    assert float(auto["net_pay"]) == 1647.00
    assert {line["description"] for line in auto["lines"]} >= {"Federal income tax (auto)", "Employer Medicare (auto)"}

    # Taxes made by hand win: Hannah's paycheck is the same as without the provider.
    hannah = paycheck_of(run, payroll["hourly"]["id"])
    assert float(hannah["employee_taxes"]) == 140 and float(hannah["employer_cost"]) == 86.8
    assert not any(line["description"].endswith("(auto)") for line in hannah["lines"])

    # Approving "sends" the direct deposits and keeps the provider's reference.
    approved = auth_client.post(f"{API}/payroll-runs/{run['id']}/approve")
    assert approved.status_code == 200, approved.text
    sent = {p["employee"]["id"]: p["deposit_reference"] for p in approved.json()["paychecks"]}
    assert sent[alex["id"]].startswith("MOCK-DD-")
    assert sent[payroll["salaried"]["id"]].startswith("MOCK-DD-")
    assert sent[payroll["hourly"]["id"]] is None  # paid by check
    assert_books_balance(auth_client)
