"""
Phase 3 - Expenses & bills: bills, vendor credits, purchase orders, paying
bills (single and batch), checks and check printing, recurring bills,
attachments / receipts, mileage and the 1099 report.
"""

import base64
from datetime import date, timedelta

import pytest

from app.core.number_words import amount_in_words

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


def make_vendor(client, name="Pat's Plumbing", **extra):
    payload = {"display_name": name}
    payload.update(extra)
    response = client.post(f"{API}/vendors", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_purchase(client, doc_type, vendor_id, amount, account="Repairs & Maintenance", **extra):
    payload = {
        "doc_type": doc_type,
        "vendor_id": vendor_id,
        "doc_date": TODAY,
        "lines": [{"account_id": account_id(client, account), "description": "Work", "rate": str(amount)}],
    }
    payload.update(extra)
    response = client.post(f"{API}/purchase-documents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def assert_books_balance(client):
    trial = client.get(f"{API}/reports/trial-balance").json()
    assert trial["summary"][0]["amount"] == trial["summary"][1]["amount"]


@pytest.fixture
def vendor(auth_client):
    return make_vendor(auth_client)


# ---------- bills and vendor credits ----------

def test_bill_posts_to_accounts_payable(auth_client, vendor):
    bill = make_purchase(auth_client, "BILL", vendor, 400, doc_number="INV-77")
    assert bill["status"] == "OPEN"
    assert bill["due_date"] == (date.today() + timedelta(days=30)).isoformat()
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 400
    assert balance_of(auth_client, "Repairs & Maintenance") == 400
    assert float(auth_client.get(f"{API}/vendors/{vendor}").json()["open_balance"]) == 400


def test_vendor_terms_set_bill_due_date(auth_client):
    terms = auth_client.get(f"{API}/terms").json()
    net15 = [term for term in terms if term["name"] == "Net 15"][0]
    vendor_id = make_vendor(auth_client, "Fast Supply", terms_id=net15["id"])
    bill = make_purchase(auth_client, "BILL", vendor_id, 100)
    assert bill["due_date"] == (date.today() + timedelta(days=15)).isoformat()


def test_pay_bill_with_vendor_credit_and_check(auth_client, vendor):
    bill = make_purchase(auth_client, "BILL", vendor, 500)
    credit = make_purchase(auth_client, "VENDOR_CREDIT", vendor, 100)
    assert float(auth_client.get(f"{API}/vendors/{vendor}").json()["open_balance"]) == 400

    checking = account_id(auth_client, "Checking")
    response = auth_client.post(
        f"{API}/bill-payments",
        json={
            "vendor_id": vendor,
            "payment_date": TODAY,
            "payment_account_id": checking,
            "payment_method": "CHECK",
            "applications": [{"bill_id": bill["id"], "amount": "500"}],
            "credits": [{"vendor_credit_id": credit["id"], "amount": "100"}],
        },
    )
    assert response.status_code == 201, response.text
    payment = response.json()
    assert float(payment["amount"]) == 400
    assert payment["check_number"] == "1001"

    assert auth_client.get(f"{API}/purchase-documents/{bill['id']}").json()["status"] == "PAID"
    assert auth_client.get(f"{API}/purchase-documents/{credit['id']}").json()["status"] == "CLOSED"
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 0
    assert balance_of(auth_client, "Checking") == -400
    assert_books_balance(auth_client)

    # Deleting the payment re-opens everything.
    assert auth_client.delete(f"{API}/bill-payments/{payment['id']}").status_code == 204
    assert auth_client.get(f"{API}/purchase-documents/{bill['id']}").json()["status"] == "OPEN"
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 400
    assert_books_balance(auth_client)


def test_batch_pay_bills_makes_one_payment_per_vendor(auth_client):
    first_vendor = make_vendor(auth_client, "Vendor A")
    second_vendor = make_vendor(auth_client, "Vendor B")
    bills = [
        make_purchase(auth_client, "BILL", first_vendor, 100),
        make_purchase(auth_client, "BILL", first_vendor, 50),
        make_purchase(auth_client, "BILL", second_vendor, 75),
    ]
    response = auth_client.post(
        f"{API}/bill-payments/batch",
        json={
            "payment_date": TODAY,
            "payment_account_id": account_id(auth_client, "Checking"),
            "payment_method": "CHECK",
            "bills": [{"bill_id": bill["id"], "amount": bill["total"]} for bill in bills],
        },
    )
    assert response.status_code == 201, response.text
    payments = response.json()
    assert len(payments) == 2
    amounts = sorted(float(payment["amount"]) for payment in payments)
    assert amounts == [75, 150]
    numbers = sorted(payment["check_number"] for payment in payments)
    assert numbers == ["1001", "1002"]


def test_cannot_overpay_a_bill(auth_client, vendor):
    bill = make_purchase(auth_client, "BILL", vendor, 100)
    response = auth_client.post(
        f"{API}/bill-payments",
        json={
            "vendor_id": vendor,
            "payment_date": TODAY,
            "payment_account_id": account_id(auth_client, "Checking"),
            "applications": [{"bill_id": bill["id"], "amount": "150"}],
        },
    )
    assert response.status_code == 422


def test_bill_paid_by_credit_card(auth_client, vendor):
    bill = make_purchase(auth_client, "BILL", vendor, 80)
    response = auth_client.post(
        f"{API}/bill-payments",
        json={
            "vendor_id": vendor,
            "payment_date": TODAY,
            "payment_account_id": account_id(auth_client, "Credit Card"),
            "payment_method": "CREDIT_CARD",
            "applications": [{"bill_id": bill["id"], "amount": "80"}],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["check_number"] is None
    assert balance_of(auth_client, "Credit Card") == 80


# ---------- purchase orders ----------

def test_purchase_order_to_bill(auth_client, vendor):
    order = make_purchase(auth_client, "PURCHASE_ORDER", vendor, 250, account="Office Supplies & Software")
    assert order["doc_number"] == "1001"
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 0  # orders do not post

    response = auth_client.post(f"{API}/purchase-documents/{order['id']}/convert-to-bill", json={"bill_date": TODAY, "bill_number": "V-9"})
    assert response.status_code == 201, response.text
    bill = response.json()
    assert bill["purchase_order_id"] == order["id"]
    assert float(bill["total"]) == 250
    assert auth_client.get(f"{API}/purchase-documents/{order['id']}").json()["status"] == "CLOSED"

    # Voiding the bill re-opens the order.
    auth_client.post(f"{API}/purchase-documents/{bill['id']}/void")
    assert auth_client.get(f"{API}/purchase-documents/{order['id']}").json()["status"] == "OPEN"
    assert_books_balance(auth_client)


# ---------- checks ----------

def test_check_numbers_and_printing(auth_client, vendor):
    checking = account_id(auth_client, "Checking")
    rent = account_id(auth_client, "Rent & Lease")

    def write_check(**extra):
        payload = {
            "kind": "CHECK",
            "vendor_id": vendor,
            "payment_account_id": checking,
            "expense_date": TODAY,
            "lines": [{"account_id": rent, "amount": "1200"}],
        }
        payload.update(extra)
        response = auth_client.post(f"{API}/expenses", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    first = write_check()
    assert first["check_number"] == "1001"
    assert first["payment_method"] == "CHECK"

    typed = write_check(check_number="2000")
    assert typed["check_number"] == "2000"
    assert auth_client.get(f"{API}/checks/next-number/{checking}").json()["next_check_number"] == 2001

    later = write_check(print_later=True)
    assert later["check_number"] is None
    waiting = auth_client.get(f"{API}/checks/to-print").json()
    assert [item["source_id"] for item in waiting] == [later["id"]]

    response = auth_client.post(
        f"{API}/checks/print",
        json={"bank_account_id": checking, "first_check_number": 2001, "items": [{"source_type": "EXPENSE", "source_id": later["id"]}]},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert auth_client.get(f"{API}/expenses/{later['id']}").json()["check_number"] == "2001"
    assert auth_client.get(f"{API}/checks/to-print").json() == []

    assert auth_client.get(f"{API}/checks/EXPENSE/{first['id']}/pdf").content.startswith(b"%PDF")


def test_checks_only_from_bank_accounts(auth_client, vendor):
    response = auth_client.post(
        f"{API}/expenses",
        json={
            "kind": "CHECK",
            "vendor_id": vendor,
            "payment_account_id": account_id(auth_client, "Credit Card"),
            "expense_date": TODAY,
            "lines": [{"account_id": account_id(auth_client, "Travel"), "amount": "10"}],
        },
    )
    assert response.status_code == 422


def test_void_expense(auth_client):
    expense = auth_client.post(
        f"{API}/expenses",
        json={
            "payment_account_id": account_id(auth_client, "Credit Card"),
            "expense_date": TODAY,
            "lines": [{"account_id": account_id(auth_client, "Travel"), "amount": "60"}],
        },
    ).json()
    assert auth_client.post(f"{API}/expenses/{expense['id']}/void").json()["is_void"] is True
    assert balance_of(auth_client, "Travel") == 0
    assert_books_balance(auth_client)


def test_amount_in_words():
    assert amount_in_words(1234.56) == "One thousand two hundred thirty-four and 56/100"
    assert amount_in_words(1000000) == "One million and 00/100"
    assert amount_in_words(15) == "Fifteen and 00/100"


# ---------- recurring bills ----------

def test_recurring_monthly_bill(auth_client, vendor):
    start = (date.today() - timedelta(days=40)).isoformat()
    response = auth_client.post(
        f"{API}/recurring",
        json={
            "name": "Office rent",
            "transaction_type": "BILL",
            "frequency": "MONTHLY",
            "start_date": start,
            "template": {"vendor_id": vendor, "lines": [{"account_id": account_id(auth_client, "Rent & Lease"), "rate": "900"}]},
        },
    )
    assert response.status_code == 201, response.text
    created = auth_client.post(f"{API}/recurring/run-due").json()["created"]
    assert len(created) == 2
    assert balance_of(auth_client, "Rent & Lease") == 1800


# ---------- attachments and receipts ----------

def test_receipt_inbox_and_attach(auth_client):
    content = base64.b64encode(b"%PDF-1.4 fake receipt").decode()
    upload = auth_client.post(
        f"{API}/attachments",
        json={"entity_type": "RECEIPT", "filename": "lunch.pdf", "mime_type": "application/pdf", "data_base64": content},
    )
    assert upload.status_code == 201, upload.text
    receipt = upload.json()
    assert [item["id"] for item in auth_client.get(f"{API}/attachments/receipts").json()] == [receipt["id"]]

    expense = auth_client.post(
        f"{API}/expenses",
        json={
            "payment_account_id": account_id(auth_client, "Credit Card"),
            "expense_date": TODAY,
            "lines": [{"account_id": account_id(auth_client, "Meals & Entertainment"), "amount": "32.50"}],
        },
    ).json()
    auth_client.put(f"{API}/attachments/{receipt['id']}/link", json={"entity_type": "EXPENSE", "entity_id": expense["id"]})

    assert auth_client.get(f"{API}/attachments/receipts").json() == []
    attached = auth_client.get(f"{API}/attachments?entity_type=EXPENSE&entity_id={expense['id']}").json()
    assert attached[0]["filename"] == "lunch.pdf"
    download = auth_client.get(f"{API}/attachments/{receipt['id']}/content")
    assert download.content == b"%PDF-1.4 fake receipt"


def test_attachment_type_is_checked(auth_client):
    response = auth_client.post(
        f"{API}/attachments",
        json={"entity_type": "RECEIPT", "filename": "virus.exe", "mime_type": "application/x-msdownload", "data_base64": "AAAA"},
    )
    assert response.status_code == 422


# ---------- mileage ----------

def test_mileage_deduction(auth_client):
    year = date.today().year
    for miles, purpose in (("120.5", "BUSINESS"), ("30", "PERSONAL"), ("79.5", "BUSINESS")):
        response = auth_client.post(f"{API}/mileage/trips", json={"trip_date": TODAY, "miles": miles, "purpose": purpose, "vehicle": "Van"})
        assert response.status_code == 201, response.text

    auth_client.put(f"{API}/mileage/rate", json={"mileage_rate": "0.70"})
    summary = auth_client.get(f"{API}/mileage/summary?year={year}").json()
    assert float(summary["business_miles"]) == 200
    assert float(summary["personal_miles"]) == 30
    assert float(summary["deduction"]) == 140


# ---------- 1099 ----------

def test_1099_summary(auth_client):
    contractor = make_vendor(auth_client, "Jane Contractor", track_1099=True, tax_id="12-3456789")
    small = make_vendor(auth_client, "Small Contractor", track_1099=True)
    not_tracked = make_vendor(auth_client, "Regular Supplier")
    checking = account_id(auth_client, "Checking")
    contractors_account = account_id(auth_client, "Contractors")

    def pay_by_check(vendor_id, amount):
        auth_client.post(
            f"{API}/expenses",
            json={
                "kind": "CHECK",
                "vendor_id": vendor_id,
                "payment_account_id": checking,
                "expense_date": TODAY,
                "lines": [{"account_id": contractors_account, "amount": amount}],
            },
        )

    pay_by_check(contractor, "500")
    pay_by_check(small, "200")  # under the 600 threshold
    pay_by_check(not_tracked, "900")  # not a 1099 vendor

    # A bill for 400, paid by check, also counts.
    bill = make_purchase(auth_client, "BILL", contractor, 400, account="Contractors")
    auth_client.post(
        f"{API}/bill-payments",
        json={
            "vendor_id": contractor,
            "payment_date": TODAY,
            "payment_account_id": checking,
            "applications": [{"bill_id": bill["id"], "amount": "400"}],
        },
    )
    # Card payments are excluded.
    auth_client.post(
        f"{API}/expenses",
        json={
            "vendor_id": contractor,
            "payment_account_id": account_id(auth_client, "Credit Card"),
            "payment_method": "CREDIT_CARD",
            "expense_date": TODAY,
            "lines": [{"account_id": contractors_account, "amount": "1000"}],
        },
    )

    report = auth_client.get(f"{API}/reports/1099-summary").json()
    assert len(report["sections"]) == 1
    section = report["sections"][0]
    assert section["title"].startswith("1099-NEC")
    assert section["rows"] == [{"label": "Jane Contractor (Tax ID 12-3456789)", "amount": "900.00", "account_id": None}]
    assert float(report["summary"][0]["amount"]) == 900


def test_ap_aging_report(auth_client, vendor):
    old_date = (date.today() - timedelta(days=75)).isoformat()
    make_purchase(auth_client, "BILL", vendor, 300, doc_date=old_date)
    make_purchase(auth_client, "BILL", vendor, 100)
    report = auth_client.get(f"{API}/reports/ap-aging").json()
    totals = {section["title"]: float(section["total"]) for section in report["sections"]}
    assert totals["Current"] == 100
    assert totals["31 - 60 days past due"] == 300
    assert float(report["summary"][0]["amount"]) == 400
