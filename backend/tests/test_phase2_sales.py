"""
Phase 2 - Sales: estimates, sales receipts, credit memos, refunds, delayed
charges, multi-invoice payments, deposits, discounts, shipping, terms,
late fees, recurring invoices, PDFs, email, statements and the customer link.
"""

import base64
from datetime import date, timedelta

import pytest

API = "/api/v1"
TODAY = date.today().isoformat()


# ---------- helpers ----------

def account_id(client, name):
    for account in client.get(f"{API}/accounts").json():
        if account["name"] == name:
            return account["id"]
    raise AssertionError(name)


def balance_of(client, name):
    for account in client.get(f"{API}/accounts").json():
        if account["name"] == name:
            return float(account["balance"])
    raise AssertionError(name)


def make_customer(client, name="Acme Corp", **extra):
    payload = {"display_name": name, "email": "billing@acme.example.com"}
    payload.update(extra)
    response = client.post(f"{API}/customers", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def line(rate, quantity="1", description="Work"):
    return {"description": description, "quantity": quantity, "rate": str(rate)}


def make_invoice(client, customer_id, rate=100, **extra):
    payload = {"customer_id": customer_id, "invoice_date": TODAY, "lines": [line(rate)]}
    payload.update(extra)
    response = client.post(f"{API}/invoices", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def make_document(client, doc_type, customer_id, rate=100, **extra):
    payload = {"doc_type": doc_type, "customer_id": customer_id, "doc_date": TODAY, "lines": [line(rate)]}
    payload.update(extra)
    response = client.post(f"{API}/sales-documents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def assert_books_balance(client):
    trial = client.get(f"{API}/reports/trial-balance").json()
    assert trial["summary"][0]["amount"] == trial["summary"][1]["amount"]
    sheet = client.get(f"{API}/reports/balance-sheet").json()
    assert sheet["summary"][0]["amount"] == sheet["summary"][1]["amount"]


@pytest.fixture
def customer(auth_client):
    return make_customer(auth_client)


# ---------- estimates and progress invoicing ----------

def test_estimate_progress_invoicing(auth_client, customer):
    estimate = make_document(auth_client, "ESTIMATE", customer, rate=1000)
    assert estimate["status"] == "PENDING"
    assert balance_of(auth_client, "Sales") == 0  # estimates do not post

    accepted = auth_client.post(f"{API}/sales-documents/{estimate['id']}/status", json={"status": "ACCEPTED"}).json()
    assert accepted["status"] == "ACCEPTED"

    first = auth_client.post(
        f"{API}/sales-documents/{estimate['id']}/convert-to-invoice", json={"invoice_date": TODAY, "percent": "40"}
    )
    assert first.status_code == 201, first.text
    assert float(first.json()["total"]) == 400
    assert first.json()["estimate_id"] == estimate["id"]

    estimate = auth_client.get(f"{API}/sales-documents/{estimate['id']}").json()
    assert estimate["status"] == "ACCEPTED"
    assert float(estimate["remaining"]) == 600

    too_much = auth_client.post(
        f"{API}/sales-documents/{estimate['id']}/convert-to-invoice", json={"invoice_date": TODAY, "percent": "70"}
    )
    assert too_much.status_code == 422

    auth_client.post(f"{API}/sales-documents/{estimate['id']}/convert-to-invoice", json={"invoice_date": TODAY, "percent": "60"})
    estimate = auth_client.get(f"{API}/sales-documents/{estimate['id']}").json()
    assert estimate["status"] == "CLOSED"
    assert balance_of(auth_client, "Sales") == 1000


def test_rejected_estimate_cannot_be_invoiced(auth_client, customer):
    estimate = make_document(auth_client, "ESTIMATE", customer)
    auth_client.post(f"{API}/sales-documents/{estimate['id']}/status", json={"status": "REJECTED"})
    response = auth_client.post(f"{API}/sales-documents/{estimate['id']}/convert-to-invoice", json={"invoice_date": TODAY})
    assert response.status_code == 422


# ---------- sales receipts, deposits ----------

def test_sales_receipt_then_bank_deposit(auth_client, customer):
    receipt = make_document(auth_client, "SALES_RECEIPT", customer, rate=250)
    assert receipt["status"] == "PAID"
    assert balance_of(auth_client, "Undeposited Funds") == 250
    assert balance_of(auth_client, "Sales") == 250

    waiting = auth_client.get(f"{API}/deposits/undeposited").json()
    assert len(waiting) == 1 and waiting[0]["source_type"] == "SALES_RECEIPT"

    response = auth_client.post(
        f"{API}/deposits",
        json={
            "deposit_date": TODAY,
            "bank_account_id": account_id(auth_client, "Checking"),
            "items": [{"source_type": "SALES_RECEIPT", "source_id": receipt["id"]}],
            "other_lines": [{"account_id": account_id(auth_client, "Owner's Investment"), "amount": "1000", "description": "Owner top-up"}],
        },
    )
    assert response.status_code == 201, response.text
    assert float(response.json()["total"]) == 1250
    assert balance_of(auth_client, "Checking") == 1250
    assert balance_of(auth_client, "Undeposited Funds") == 0
    assert auth_client.get(f"{API}/deposits/undeposited").json() == []

    # A deposited receipt cannot be voided.
    assert auth_client.post(f"{API}/sales-documents/{receipt['id']}/void").status_code == 422
    assert_books_balance(auth_client)


# ---------- credit memos, refunds, multi-invoice payments ----------

def test_payment_across_invoices_with_credit_and_overpayment(auth_client, customer):
    first = make_invoice(auth_client, customer, rate=300)
    second = make_invoice(auth_client, customer, rate=200)
    memo = make_document(auth_client, "CREDIT_MEMO", customer, rate=50)
    assert memo["status"] == "OPEN"

    customer_row = auth_client.get(f"{API}/customers/{customer}").json()
    assert float(customer_row["open_balance"]) == 450  # 300 + 200 - 50

    credits = auth_client.get(f"{API}/customers/{customer}/credits").json()
    assert credits[0]["source_type"] == "CREDIT_MEMO" and float(credits[0]["remaining"]) == 50

    # Pay both invoices with 500 cash + the 50 credit memo: 50 is left over.
    response = auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer,
            "payment_date": TODAY,
            "amount": "500",
            "applications": [{"invoice_id": first["id"], "amount": "300"}, {"invoice_id": second["id"], "amount": "200"}],
            "credits": [{"source_type": "CREDIT_MEMO", "source_id": memo["id"], "amount": "50"}],
        },
    )
    assert response.status_code == 201, response.text
    payment = response.json()
    assert float(payment["unapplied_amount"]) == 50
    assert len(payment["applications"]) == 2

    assert auth_client.get(f"{API}/invoices/{first['id']}").json()["status"] == "PAID"
    assert auth_client.get(f"{API}/sales-documents/{memo['id']}").json()["status"] == "CLOSED"
    assert float(auth_client.get(f"{API}/customers/{customer}").json()["open_balance"]) == -50

    # The overpayment is now a credit that pays the next invoice with no new money.
    third = make_invoice(auth_client, customer, rate=50)
    response = auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer,
            "payment_date": TODAY,
            "amount": "0",
            "applications": [{"invoice_id": third["id"], "amount": "50"}],
            "credits": [{"source_type": "PAYMENT", "source_id": payment["id"], "amount": "50"}],
        },
    )
    assert response.status_code == 201, response.text
    assert auth_client.get(f"{API}/invoices/{third['id']}").json()["status"] == "PAID"
    assert float(auth_client.get(f"{API}/customers/{customer}").json()["open_balance"]) == 0
    assert_books_balance(auth_client)


def test_credits_must_be_applied_to_invoices(auth_client, customer):
    memo = make_document(auth_client, "CREDIT_MEMO", customer, rate=50)
    response = auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer,
            "payment_date": TODAY,
            "amount": "0",
            "credits": [{"source_type": "CREDIT_MEMO", "source_id": memo["id"], "amount": "50"}],
        },
    )
    assert response.status_code == 422


def test_refund_receipt_reduces_income_and_bank(auth_client, customer):
    checking = account_id(auth_client, "Checking")
    make_document(auth_client, "SALES_RECEIPT", customer, rate=300, money_account_id=checking)
    refund = make_document(auth_client, "REFUND_RECEIPT", customer, rate=120, money_account_id=checking)
    assert refund["status"] == "PAID"
    assert balance_of(auth_client, "Checking") == 180
    assert balance_of(auth_client, "Sales") == 180
    assert_books_balance(auth_client)


def test_refund_receipt_needs_an_account(auth_client, customer):
    response = auth_client.post(
        f"{API}/sales-documents",
        json={"doc_type": "REFUND_RECEIPT", "customer_id": customer, "doc_date": TODAY, "lines": [line(10)]},
    )
    assert response.status_code == 422


# ---------- delayed charges and credits ----------

def test_delayed_charges_and_credits_go_onto_an_invoice(auth_client, customer):
    charge = make_document(auth_client, "DELAYED_CHARGE", customer, rate=80)
    credit = make_document(auth_client, "DELAYED_CREDIT", customer, rate=30)
    assert balance_of(auth_client, "Sales") == 0  # no posting yet

    invoice = make_invoice(auth_client, customer, rate=100, delayed_document_ids=[charge["id"], credit["id"]])
    assert float(invoice["total"]) == 150  # 100 + 80 - 30
    assert len(invoice["lines"]) == 3
    assert auth_client.get(f"{API}/sales-documents/{charge['id']}").json()["status"] == "CLOSED"

    # Using it twice is blocked.
    again = auth_client.post(
        f"{API}/invoices",
        json={"customer_id": customer, "invoice_date": TODAY, "lines": [line(10)], "delayed_document_ids": [charge["id"]]},
    )
    assert again.status_code == 422

    # Voiding the invoice gives the delayed charge back.
    auth_client.post(f"{API}/invoices/{invoice['id']}/void")
    assert auth_client.get(f"{API}/sales-documents/{charge['id']}").json()["status"] == "OPEN"
    assert_books_balance(auth_client)


# ---------- discounts, shipping, deposits, terms ----------

def test_discount_and_shipping_post_to_their_accounts(auth_client, customer):
    invoice = make_invoice(
        auth_client,
        customer,
        rate=1000,
        discount_type="PERCENT",
        discount_value="10",
        shipping_amount="25",
    )
    assert float(invoice["subtotal"]) == 1000
    assert float(invoice["discount_amount"]) == 100
    assert float(invoice["total"]) == 925

    report = auth_client.get(f"{API}/reports/profit-and-loss").json()
    income = {row["label"]: float(row["amount"]) for row in report["sections"][0]["rows"]}
    assert income["Sales"] == 1000
    assert income["Shipping Income"] == 25
    assert income["Discounts Given"] == -100
    assert float(report["summary"][0]["amount"]) == 925
    assert_books_balance(auth_client)


def test_discount_cannot_exceed_subtotal(auth_client, customer):
    response = auth_client.post(
        f"{API}/invoices",
        json={"customer_id": customer, "invoice_date": TODAY, "lines": [line(50)], "discount_type": "AMOUNT", "discount_value": "60"},
    )
    assert response.status_code == 422


def test_deposit_taken_when_invoice_is_created(auth_client, customer):
    invoice = make_invoice(auth_client, customer, rate=500, deposit_amount="200", deposit_account_id=account_id(auth_client, "Checking"))
    invoice = auth_client.get(f"{API}/invoices/{invoice['id']}").json()
    assert invoice["status"] == "PARTIALLY_PAID"
    assert float(invoice["balance_due"]) == 300
    assert balance_of(auth_client, "Checking") == 200


def test_customer_terms_set_the_due_date(auth_client):
    terms = auth_client.get(f"{API}/terms").json()
    net15 = [term for term in terms if term["name"] == "Net 15"][0]
    customer_id = make_customer(auth_client, "Termed Co", terms_id=net15["id"])

    invoice = make_invoice(auth_client, customer_id)
    expected = (date.today() + timedelta(days=15)).isoformat()
    assert invoice["due_date"] == expected
    assert invoice["terms_id"] == net15["id"]


# ---------- late fees ----------

def test_late_fee_is_added_once(auth_client, customer):
    settings = auth_client.get(f"{API}/company/sales-settings").json()
    settings.update({"late_fee_enabled": True, "late_fee_type": "FIXED", "late_fee_amount": "25", "late_fee_grace_days": 0})
    assert auth_client.put(f"{API}/company/sales-settings", json=settings).status_code == 200

    old_date = (date.today() - timedelta(days=60)).isoformat()
    invoice = make_invoice(auth_client, customer, rate=100, invoice_date=old_date)

    result = auth_client.post(f"{API}/invoices/apply-late-fees").json()
    assert result["count"] == 1
    invoice = auth_client.get(f"{API}/invoices/{invoice['id']}").json()
    assert float(invoice["total"]) == 125
    assert invoice["lines"][-1]["is_late_fee"] is True
    assert balance_of(auth_client, "Late Fee Income") == 25

    assert auth_client.post(f"{API}/invoices/apply-late-fees").json()["count"] == 0
    assert_books_balance(auth_client)


# ---------- recurring invoices ----------

def test_recurring_invoice(auth_client, customer):
    start = (date.today() - timedelta(days=14)).isoformat()
    response = auth_client.post(
        f"{API}/recurring",
        json={
            "name": "Weekly cleaning",
            "transaction_type": "INVOICE",
            "frequency": "WEEKLY",
            "interval": 1,
            "start_date": start,
            "template": {"customer_id": customer, "lines": [line(75)]},
        },
    )
    assert response.status_code == 201, response.text
    created = auth_client.post(f"{API}/recurring/run-due").json()["created"]
    assert len(created) == 3  # 14 days ago, 7 days ago, today
    assert len(auth_client.get(f"{API}/invoices").json()) == 3


# ---------- PDFs, email, statements ----------

def test_pdfs_are_generated(auth_client, customer):
    invoice = make_invoice(auth_client, customer, discount_type="AMOUNT", discount_value="10", shipping_amount="5")
    estimate = make_document(auth_client, "ESTIMATE", customer)

    for url in (
        f"{API}/invoices/{invoice['id']}/pdf",
        f"{API}/sales-documents/{estimate['id']}/pdf",
        f"{API}/customers/{customer}/statement/pdf",
    ):
        response = auth_client.get(url)
        assert response.status_code == 200, url
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


def test_logo_and_invoice_style_are_used(auth_client, customer):
    # A 1x1 PNG
    png = base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
        )
    ).decode()
    assert auth_client.put(f"{API}/company/logo", json={"mime_type": "image/png", "data_base64": png}).status_code == 200
    assert auth_client.get(f"{API}/company/logo").json()["data_url"].startswith("data:image/png;base64,")

    settings = auth_client.get(f"{API}/company/sales-settings").json()
    settings.update({"invoice_template": "modern", "invoice_accent_color": "#1d4ed8", "invoice_footer": "Thanks!"})
    auth_client.put(f"{API}/company/sales-settings", json=settings)

    invoice = make_invoice(auth_client, customer)
    assert auth_client.get(f"{API}/invoices/{invoice['id']}/pdf").content.startswith(b"%PDF")


def test_email_invoice_is_recorded_in_email_log(auth_client, customer):
    invoice = make_invoice(auth_client, customer)
    response = auth_client.post(f"{API}/invoices/{invoice['id']}/email", json={"to": "billing@acme.example.com"})
    assert response.status_code == 200, response.text

    log = auth_client.get(f"{API}/email-log").json()
    assert log[0]["to_address"] == "billing@acme.example.com"
    assert log[0]["attachment_name"] == f"Invoice-{invoice['invoice_number']}.pdf"
    assert log[0]["status"] == "LOGGED"
    assert auth_client.get(f"{API}/invoices/{invoice['id']}").json()["last_emailed_at"] is not None


def test_overdue_reminders(auth_client, customer):
    settings = auth_client.get(f"{API}/company/sales-settings").json()
    settings.update({"reminders_enabled": True, "reminder_days_after_due": 3})
    auth_client.put(f"{API}/company/sales-settings", json=settings)

    make_invoice(auth_client, customer, invoice_date=(date.today() - timedelta(days=45)).isoformat())
    make_invoice(auth_client, customer)  # not overdue

    assert auth_client.post(f"{API}/invoices/send-reminders").json()["count"] == 1
    assert auth_client.post(f"{API}/invoices/send-reminders").json()["count"] == 0  # not again so soon


def test_balance_forward_statement(auth_client, customer):
    last_month = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    make_invoice(auth_client, customer, rate=100, invoice_date=last_month)
    make_invoice(auth_client, customer, rate=40)

    statement = auth_client.get(f"{API}/customers/{customer}/statement").json()
    assert float(statement["opening_balance"]) == 100
    assert float(statement["closing_balance"]) == 140
    assert len(statement["lines"]) == 1

    open_items = auth_client.get(f"{API}/customers/{customer}/statement?statement_type=OPEN_ITEM").json()
    assert len(open_items["lines"]) == 2


# ---------- customer link ----------

def test_public_invoice_link(auth_client, client, customer):
    invoice = make_invoice(auth_client, customer, rate=99)
    url = auth_client.post(f"{API}/invoices/{invoice['id']}/share-link").json()["url"]
    token = url.rsplit("/", 1)[1]

    # The customer is not signed in.
    del client.headers["Authorization"]
    public = client.get(f"{API}/public/invoices/{token}")
    assert public.status_code == 200
    assert float(public.json()["balance_due"]) == 99
    assert public.json()["online_payment_enabled"] is False

    assert client.get(f"{API}/public/invoices/{token}/pdf").content.startswith(b"%PDF")
    assert client.post(f"{API}/public/invoices/{token}/pay", json={}).status_code == 422
    assert client.get(f"{API}/public/invoices/not-a-real-token").status_code == 404


def test_void_rules(auth_client, customer):
    memo = make_document(auth_client, "CREDIT_MEMO", customer, rate=20)
    invoice = make_invoice(auth_client, customer, rate=20)
    auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer,
            "payment_date": TODAY,
            "amount": "0",
            "applications": [{"invoice_id": invoice["id"], "amount": "20"}],
            "credits": [{"source_type": "CREDIT_MEMO", "source_id": memo["id"], "amount": "20"}],
        },
    )
    assert auth_client.post(f"{API}/sales-documents/{memo['id']}/void").status_code == 422

    unused = make_document(auth_client, "CREDIT_MEMO", customer, rate=15)
    assert auth_client.post(f"{API}/sales-documents/{unused['id']}/void").json()["status"] == "VOID"
    assert_books_balance(auth_client)
