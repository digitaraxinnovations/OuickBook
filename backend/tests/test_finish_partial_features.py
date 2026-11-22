"""
The last three partly-done roadmap items:
  - products on the Import & export page
  - attachments on journal entries, payments and deposits
  - foreign currency for vendors, bills, vendor credits, expenses and bill payments
"""

import base64
from datetime import date, timedelta

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def post(client, path, payload, expected=201):
    response = client.post(f"{API}{path}", json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def turn_on_euros(client, rate="1.10"):
    settings = client.get(f"{API}/company/advanced-settings").json()
    settings["multicurrency_enabled"] = True
    client.put(f"{API}/company/advanced-settings", json=settings)
    post(client, "/currencies", {"code": "EUR", "name": "Euro"})
    post(client, "/exchange-rates", {"currency_code": "EUR", "rate_date": YESTERDAY, "rate": rate})


def euro_vendor(client, name="Lyon Supplies"):
    return post(client, "/vendors", {"display_name": name, "currency_code": "EUR"})["id"]


# ------------------------------------------------------------------ item 7
def test_products_on_the_import_export_page(auth_client):
    csv_text = "Name,SKU,Type,Sales price,Purchase cost\nHedge trimming,,Service,75,0\nSprinkler head,SPR-4,Non-inventory,14.50,6.20\n"
    result = post(auth_client, "/data/products/import", {"content": csv_text}, expected=200)
    assert result == {"created": 2, "updated": 0, "errors": []}

    exported = auth_client.get(f"{API}/data/products/export")
    assert exported.status_code == 200
    assert "Sprinkler head" in exported.text and exported.text.startswith("Name,SKU,Type")

    bad = post(auth_client, "/data/products/import", {"content": "Name,Type\nBroken,Spaceship\n"}, expected=200)
    assert bad["created"] == 0 and bad["errors"]  # all or nothing


# ------------------------------------------------------------------ item 6
def test_attachments_on_journal_entries_payments_and_deposits(auth_client):
    customer = make_customer(auth_client, "Attach Co")
    invoice = post(auth_client, "/invoices", {"customer_id": customer, "invoice_date": TODAY, "lines": [{"description": "Work", "quantity": "1", "rate": "100"}]})
    payment = post(
        auth_client,
        "/payments",
        {"customer_id": customer, "payment_date": TODAY, "amount": "100", "applications": [{"invoice_id": invoice["id"], "amount": "100"}]},
    )
    deposit = post(
        auth_client,
        "/deposits",
        {"deposit_date": TODAY, "bank_account_id": account_id(auth_client, "Checking"), "items": [{"source_type": "PAYMENT", "source_id": payment["id"]}]},
    )
    entry_id = auth_client.get(f"{API}/journal-entries").json()[0]["id"]

    content = base64.b64encode(b"scan").decode()
    for entity_type, entity_id in (("JOURNAL_ENTRY", entry_id), ("PAYMENT", payment["id"]), ("DEPOSIT", deposit["id"])):
        post(auth_client, "/attachments", {"entity_type": entity_type, "entity_id": entity_id, "filename": "scan.pdf", "mime_type": "application/pdf", "data_base64": content})
        listed = auth_client.get(f"{API}/attachments", params={"entity_type": entity_type, "entity_id": entity_id}).json()
        assert [item["filename"] for item in listed] == ["scan.pdf"]


# ------------------------------------------------------------------ item 5
def test_foreign_currency_bill_and_payment(auth_client):
    turn_on_euros(auth_client, "1.10")
    vendor = euro_vendor(auth_client)
    utilities = account_id(auth_client, "Utilities")

    bill = post(
        auth_client,
        "/purchase-documents",
        {"doc_type": "BILL", "vendor_id": vendor, "doc_date": TODAY, "lines": [{"account_id": utilities, "quantity": "1", "rate": "100"}]},
    )
    assert bill["currency_code"] == "EUR" and float(bill["exchange_rate"]) == 1.1
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 110  # owed, in dollars
    assert balance_of(auth_client, "Utilities") == 110

    # The vendor list and the A/P aging show the home currency value.
    vendors = {v["id"]: v for v in auth_client.get(f"{API}/vendors").json()}
    assert float(vendors[vendor]["open_balance"]) == 110

    # The euro got dearer: paying 100 EUR now costs $120, a $10 exchange loss.
    payment = post(
        auth_client,
        "/bill-payments",
        {
            "vendor_id": vendor,
            "payment_date": TODAY,
            "payment_account_id": account_id(auth_client, "Checking"),
            "payment_method": "BANK_TRANSFER",
            "exchange_rate": "1.20",
            "applications": [{"bill_id": bill["id"], "amount": "100"}],
        },
    )
    assert payment["currency_code"] == "EUR"
    assert balance_of(auth_client, "Accounts Payable (A/P)") == 0
    assert balance_of(auth_client, "Checking") == -120
    assert balance_of(auth_client, "Exchange Gain or Loss") == 10  # a loss (debit to the account)
    assert_books_balance(auth_client)

    # Once a vendor has bills, their currency is fixed.
    change = auth_client.put(f"{API}/vendors/{vendor}", json={"display_name": "Lyon Supplies", "currency_code": None})
    assert change.status_code == 422


def test_foreign_currency_expense_and_stock_cost(auth_client):
    turn_on_euros(auth_client, "1.10")
    vendor = euro_vendor(auth_client, "Paris Garden Shop")

    expense = post(
        auth_client,
        "/expenses",
        {
            "vendor_id": vendor,
            "payment_account_id": account_id(auth_client, "Checking"),
            "expense_date": TODAY,
            "exchange_rate": "1.25",
            "lines": [{"account_id": account_id(auth_client, "Utilities"), "amount": "40"}],
        },
    )
    assert expense["currency_code"] == "EUR"
    assert balance_of(auth_client, "Utilities") == 50
    assert balance_of(auth_client, "Checking") == -50

    # Stock bought in euros is valued in dollars.
    product = post(auth_client, "/products", {"name": "Imported shears", "product_type": "INVENTORY", "sales_price": "30", "purchase_cost": "10"})
    post(
        auth_client,
        "/purchase-documents",
        {"doc_type": "BILL", "vendor_id": vendor, "doc_date": TODAY, "lines": [{"product_id": product["id"], "quantity": "4", "rate": "10"}]},
    )
    assert balance_of(auth_client, "Inventory Asset") == 44
    assert_books_balance(auth_client)

    # Home currency vendors are unchanged.
    plain = post(auth_client, "/vendors", {"display_name": "Local Hardware"})["id"]
    home_bill = post(
        auth_client,
        "/purchase-documents",
        {"doc_type": "BILL", "vendor_id": plain, "doc_date": TODAY, "lines": [{"account_id": account_id(auth_client, "Utilities"), "quantity": "1", "rate": "20"}]},
    )
    assert home_bill["currency_code"] is None and float(home_bill["exchange_rate"]) == 1
