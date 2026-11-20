"""
Phase 5 - Taxes: agencies, rates, combined codes, tax on sales forms,
taxable items and exempt customers, filing periods, payments, adjustments,
the liability report and income tax categories.
"""

from datetime import date

import pytest

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer

YEAR = date.today().year
JULY = date(YEAR, 7, 15).isoformat()  # inside a filing period that is already over
STATE_ACCOUNT = "State Revenue Dept Payable"


def setup_taxes(client):
    agency = client.post(
        f"{API}/taxes/agencies",
        json={"name": "State Revenue Dept", "filing_frequency": "QUARTERLY", "start_date": f"{YEAR}-01-01"},
    )
    assert agency.status_code == 201, agency.text
    agency_id = agency.json()["id"]

    state = client.post(f"{API}/taxes/rates", json={"name": "State", "agency_id": agency_id, "rate": "6"}).json()
    county = client.post(
        f"{API}/taxes/rates", json={"name": "County", "agency_id": agency_id, "rate": "1.25", "create_code": False}
    ).json()
    combined = client.post(f"{API}/taxes/codes", json={"name": "State + County", "rate_ids": [state["id"], county["id"]]})
    assert combined.status_code == 201, combined.text
    return {"agency_id": agency_id, "code": combined.json(), "state_rate": state}


def taxed_invoice(client, customer_id, tax_code_id, invoice_date=TODAY, **extra):
    payload = {
        "customer_id": customer_id,
        "invoice_date": invoice_date,
        "tax_code_id": tax_code_id,
        "lines": [
            {"description": "Taxable goods", "quantity": "1", "rate": "1000"},
            {"description": "Labour", "quantity": "1", "rate": "200", "taxable": False},
        ],
    }
    payload.update(extra)
    response = client.post(f"{API}/invoices", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def taxes(auth_client):
    return setup_taxes(auth_client)


def test_agency_creates_liability_sub_account_and_codes(auth_client, taxes):
    accounts = {a["name"]: a for a in auth_client.get(f"{API}/accounts").json()}
    assert STATE_ACCOUNT in accounts
    assert accounts[STATE_ACCOUNT]["parent_id"] == accounts["Sales Tax Payable"]["id"]

    codes = {c["name"]: c for c in auth_client.get(f"{API}/taxes/codes").json()}
    assert float(codes["State + County"]["total_rate"]) == 7.25
    assert "State" in codes  # created together with the rate
    assert "County" not in codes  # create_code was false

    duplicate = auth_client.post(
        f"{API}/taxes/agencies", json={"name": "state revenue dept", "start_date": f"{YEAR}-01-01"}
    )
    assert duplicate.status_code == 409


def test_invoice_tax_with_discount_shipping_and_non_taxable_line(auth_client, taxes):
    customer = make_customer(auth_client)
    invoice = taxed_invoice(
        auth_client, customer, taxes["code"]["id"], discount_type="PERCENT", discount_value="10", shipping_amount="50"
    )
    # subtotal 1200, discount 120; taxable 1000 less its 100 share of the discount = 900
    # state 6% = 54.00, county 1.25% = 11.25
    assert float(invoice["tax_amount"]) == 65.25
    assert float(invoice["total"]) == 1200 - 120 + 50 + 65.25
    assert invoice["lines"][0]["taxable"] is True
    assert invoice["lines"][1]["taxable"] is False

    assert balance_of(auth_client, STATE_ACCOUNT) == 65.25
    assert balance_of(auth_client, "Accounts Receivable (A/R)") == 1195.25
    assert_books_balance(auth_client)

    report = auth_client.get(f"{API}/reports/sales-tax-liability?start_date={YEAR}-01-01&end_date={YEAR}-12-31").json()
    assert report["summary"][0]["amount"] == "900.00"  # counted once, not once per rate
    assert report["summary"][1]["amount"] == "65.25"

    pdf = auth_client.get(f"{API}/invoices/{invoice['id']}/pdf")
    assert pdf.status_code == 200


def test_product_taxable_flag_and_exempt_customer(auth_client, taxes):
    code_id = taxes["code"]["id"]
    product = auth_client.post(f"{API}/products", json={"name": "Consulting", "sales_price": "100", "taxable": False}).json()
    assert product["taxable"] is False

    customer = make_customer(auth_client)
    invoice = auth_client.post(
        f"{API}/invoices",
        json={
            "customer_id": customer,
            "invoice_date": TODAY,
            "tax_code_id": code_id,
            "lines": [{"product_id": product["id"], "quantity": "2", "rate": "100"}],
        },
    ).json()
    assert float(invoice["tax_amount"]) == 0

    exempt = make_customer(auth_client, "Charity", tax_exempt=True, exemption_reason="Non-profit", default_tax_code_id=code_id)
    invoice = taxed_invoice(auth_client, exempt, code_id)
    assert float(invoice["tax_amount"]) == 0
    assert invoice["tax_code_id"] == code_id
    assert balance_of(auth_client, STATE_ACCOUNT) == 0


def test_sales_receipt_credit_memo_and_void(auth_client, taxes):
    code_id = taxes["code"]["id"]
    customer = make_customer(auth_client)
    line = [{"description": "Goods", "quantity": "1", "rate": "100"}]

    receipt = auth_client.post(
        f"{API}/sales-documents",
        json={"doc_type": "SALES_RECEIPT", "customer_id": customer, "doc_date": TODAY, "tax_code_id": code_id, "lines": line},
    ).json()
    assert float(receipt["tax_amount"]) == 7.25
    assert float(receipt["total"]) == 107.25

    memo = auth_client.post(
        f"{API}/sales-documents",
        json={"doc_type": "CREDIT_MEMO", "customer_id": customer, "doc_date": TODAY, "tax_code_id": code_id, "lines": line},
    ).json()
    assert float(memo["tax_amount"]) == 7.25
    assert balance_of(auth_client, STATE_ACCOUNT) == 0  # the credit memo gave the tax back

    estimate = auth_client.post(
        f"{API}/sales-documents",
        json={"doc_type": "ESTIMATE", "customer_id": customer, "doc_date": TODAY, "tax_code_id": code_id, "lines": line},
    ).json()
    assert float(estimate["total"]) == 107.25
    assert balance_of(auth_client, STATE_ACCOUNT) == 0  # estimates do not post

    invoice = taxed_invoice(auth_client, customer, code_id)
    assert balance_of(auth_client, STATE_ACCOUNT) == 72.50
    auth_client.post(f"{API}/invoices/{invoice['id']}/void")
    assert balance_of(auth_client, STATE_ACCOUNT) == 0

    report = auth_client.get(f"{API}/reports/sales-tax-liability?start_date={YEAR}-01-01&end_date={YEAR}-12-31").json()
    assert report["summary"][1]["amount"] == "0.00"
    assert_books_balance(auth_client)


def test_progress_invoice_keeps_tax(auth_client, taxes):
    code_id = taxes["code"]["id"]
    customer = make_customer(auth_client)
    estimate = auth_client.post(
        f"{API}/sales-documents",
        json={
            "doc_type": "ESTIMATE",
            "customer_id": customer,
            "doc_date": TODAY,
            "tax_code_id": code_id,
            "lines": [{"description": "Job", "quantity": "1", "rate": "1000"}],
        },
    ).json()
    invoice = auth_client.post(
        f"{API}/sales-documents/{estimate['id']}/convert-to-invoice", json={"invoice_date": TODAY, "percent": "50"}
    )
    assert invoice.status_code == 201, invoice.text
    assert float(invoice.json()["tax_amount"]) == 36.25


def test_periods_payment_and_adjustment(auth_client, taxes):
    agency_id = taxes["agency_id"]
    customer = make_customer(auth_client)
    taxed_invoice(auth_client, customer, taxes["code"]["id"], invoice_date=JULY)  # 72.50 tax

    periods = auth_client.get(f"{API}/taxes/periods?agency_id={agency_id}").json()
    q3 = [p for p in periods if p["period_start"] == f"{YEAR}-07-01"][0]
    assert q3["period_end"] == f"{YEAR}-09-30"
    assert q3["status"] == "DUE"
    assert float(q3["balance"]) == 72.50

    # A filing discount of 2.50 lowers what is owed.
    other_income = account_id(auth_client, "Other Income")
    adjustment = auth_client.post(
        f"{API}/taxes/adjustments",
        json={"agency_id": agency_id, "adjustment_date": JULY, "amount": "-2.50", "account_id": other_income, "reason": "Early filing discount"},
    )
    assert adjustment.status_code == 201, adjustment.text

    payment = auth_client.post(
        f"{API}/taxes/payments",
        json={
            "agency_id": agency_id,
            "payment_date": f"{YEAR}-10-10",
            "period_start": f"{YEAR}-07-01",
            "period_end": f"{YEAR}-09-30",
            "amount": "70.00",
            "payment_account_id": account_id(auth_client, "Checking"),
        },
    )
    assert payment.status_code == 201, payment.text

    periods = auth_client.get(f"{API}/taxes/periods?agency_id={agency_id}").json()
    q3 = [p for p in periods if p["period_start"] == f"{YEAR}-07-01"][0]
    assert q3["status"] == "PAID"
    assert float(q3["balance"]) == 0
    assert balance_of(auth_client, STATE_ACCOUNT) == 0
    assert_books_balance(auth_client)

    bad = auth_client.post(
        f"{API}/taxes/payments",
        json={
            "agency_id": agency_id,
            "payment_date": TODAY,
            "period_start": f"{YEAR}-07-01",
            "period_end": f"{YEAR}-09-30",
            "amount": "1",
            "payment_account_id": account_id(auth_client, "Accounts Receivable (A/R)"),
        },
    )
    assert bad.status_code == 422


def test_tax_categories_and_schedule_report(auth_client, taxes):
    lines = auth_client.get(f"{API}/taxes/tax-lines").json()
    assert "SCHC_18" in lines

    accounts = {a["name"]: a for a in auth_client.get(f"{API}/accounts").json()}
    assert accounts["Sales"]["tax_line"] == "SCHC_1"

    bad = auth_client.post(
        f"{API}/accounts",
        json={"name": "Weird", "account_type": "EXPENSE", "detail_type": "Other", "tax_line": "NOPE"},
    )
    assert bad.status_code == 422

    make_invoice_customer = make_customer(auth_client)
    taxed_invoice(auth_client, make_invoice_customer, taxes["code"]["id"])
    report = auth_client.get(f"{API}/reports/tax-schedule?start_date={YEAR}-01-01&end_date={YEAR}-12-31").json()
    labels = {row["label"]: row["amount"] for row in report["sections"][0]["rows"]}
    assert labels["Line 1 - Gross receipts or sales"] == "1200.00"
    assert report["summary"][0]["amount"] == "1200.00"


def test_rate_lookup_is_behind_an_interface(auth_client):
    status = auth_client.get(f"{API}/taxes/lookup/status").json()
    assert status == {"enabled": False, "provider": "none"}
    response = auth_client.post(f"{API}/taxes/lookup", json={"address": "1 Main St"})
    assert response.status_code == 422
