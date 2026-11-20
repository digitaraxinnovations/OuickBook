"""
Phase 6 - Inventory: FIFO stock, cost of goods sold, purchases of items,
returns, adjustments, valuation reports, bundles, categories, price rules
and product import/export.
"""

from datetime import date

import pytest

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer

YEAR = date.today().year
JAN = f"{YEAR}-01-02"


def make_item(client, name="Widget", **extra):
    payload = {"name": name, "product_type": "INVENTORY", "sales_price": "20", "purchase_cost": "4"}
    payload.update(extra)
    response = client.post(f"{API}/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def get_product(client, product_id):
    for product in client.get(f"{API}/products").json():
        if product["id"] == product_id:
            return product
    raise AssertionError(product_id)


def make_vendor(client, name="Supplier"):
    response = client.post(f"{API}/vendors", json={"display_name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def bill_items(client, vendor_id, product_id, quantity, rate, doc_type="BILL"):
    response = client.post(
        f"{API}/purchase-documents",
        json={
            "doc_type": doc_type,
            "vendor_id": vendor_id,
            "doc_date": TODAY,
            "lines": [{"product_id": product_id, "quantity": str(quantity), "rate": str(rate)}],
        },
    )
    return response


def sell(client, customer_id, product_id, quantity, rate=20, doc_type=None):
    lines = [{"product_id": product_id, "quantity": str(quantity), "rate": str(rate)}]
    if doc_type is None:
        return client.post(f"{API}/invoices", json={"customer_id": customer_id, "invoice_date": TODAY, "lines": lines})
    return client.post(
        f"{API}/sales-documents",
        json={"doc_type": doc_type, "customer_id": customer_id, "doc_date": TODAY, "lines": lines},
    )


@pytest.fixture
def stocked(auth_client):
    """Widget: 10 on hand at 4.00 (starting), then a bill of 10 at 6.00."""
    item = make_item(auth_client, initial_quantity="10", as_of_date=JAN)
    vendor = make_vendor(auth_client)
    response = bill_items(auth_client, vendor, item["id"], 10, 6)
    assert response.status_code == 201, response.text
    return {"item": item, "vendor": vendor, "bill": response.json()}


def test_starting_stock_and_bill(auth_client, stocked):
    item = get_product(auth_client, stocked["item"]["id"])
    assert float(item["quantity_on_hand"]) == 20
    assert balance_of(auth_client, "Inventory Asset") == 100  # 40 + 60
    assert balance_of(auth_client, "Opening Balance Equity") == 40
    assert stocked["bill"]["lines"][0]["product_id"] == item["id"]
    assert_books_balance(auth_client)


def test_fifo_cost_of_goods_sold_and_void(auth_client, stocked):
    customer = make_customer(auth_client)
    item_id = stocked["item"]["id"]

    invoice = sell(auth_client, customer, item_id, 15)
    assert invoice.status_code == 201, invoice.text
    # FIFO: 10 at 4.00 + 5 at 6.00 = 70
    assert balance_of(auth_client, "Cost of Goods Sold") == 70
    assert balance_of(auth_client, "Inventory Asset") == 30
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 5

    too_many = sell(auth_client, customer, item_id, 6)
    assert too_many.status_code == 422
    assert "on hand" in too_many.json()["detail"]

    summary = auth_client.get(f"{API}/reports/inventory-valuation-summary").json()
    assert summary["summary"][0]["amount"] == "30.00"

    # The bill's stock was partly sold, so the bill cannot be voided.
    blocked = auth_client.post(f"{API}/purchase-documents/{stocked['bill']['id']}/void")
    assert blocked.status_code == 422

    voided = auth_client.post(f"{API}/invoices/{invoice.json()['id']}/void")
    assert voided.status_code == 200, voided.text
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 20
    assert balance_of(auth_client, "Cost of Goods Sold") == 0
    assert balance_of(auth_client, "Inventory Asset") == 100

    # Now nothing from the bill is used, so it can be voided.
    assert auth_client.post(f"{API}/purchase-documents/{stocked['bill']['id']}/void").status_code == 200
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 10
    assert balance_of(auth_client, "Inventory Asset") == 40
    assert_books_balance(auth_client)


def test_returns_vendor_credit_and_expense(auth_client, stocked):
    customer = make_customer(auth_client)
    item_id = stocked["item"]["id"]

    assert sell(auth_client, customer, item_id, 3, doc_type="SALES_RECEIPT").status_code == 201  # 3 at 4.00 = 12
    memo = sell(auth_client, customer, item_id, 1, doc_type="CREDIT_MEMO")
    assert memo.status_code == 201, memo.text
    # Returned at the latest cost (6.00)
    assert balance_of(auth_client, "Cost of Goods Sold") == 6
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 18

    # Return 2 to the vendor for a 10.00 credit: FIFO cost is 2 at 4.00 = 8.00, so 2.00 less COGS.
    credit = bill_items(auth_client, stocked["vendor"], item_id, 2, 5, doc_type="VENDOR_CREDIT")
    assert credit.status_code == 201, credit.text
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 16
    assert balance_of(auth_client, "Cost of Goods Sold") == 4

    # An expense with an item line adds stock.
    expense = auth_client.post(
        f"{API}/expenses",
        json={
            "payment_account_id": account_id(auth_client, "Checking"),
            "expense_date": TODAY,
            "lines": [{"product_id": item_id, "quantity": "2", "amount": "10"}],
        },
    )
    assert expense.status_code == 201, expense.text
    assert expense.json()["lines"][0]["account"]["name"] == "Inventory Asset"
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 18

    summary = auth_client.get(f"{API}/reports/inventory-valuation-summary").json()
    assert float(summary["summary"][0]["amount"]) == balance_of(auth_client, "Inventory Asset")
    assert_books_balance(auth_client)


def test_inventory_adjustments(auth_client, stocked):
    item_id = stocked["item"]["id"]
    shrink = auth_client.post(
        f"{API}/inventory-adjustments",
        json={"adjustment_date": TODAY, "memo": "Count", "lines": [{"product_id": item_id, "quantity_change": "-3"}]},
    )
    assert shrink.status_code == 201, shrink.text
    assert float(shrink.json()["lines"][0]["value_change"]) == -12
    assert balance_of(auth_client, "Inventory Shrinkage") == 12

    found = auth_client.post(
        f"{API}/inventory-adjustments",
        json={"adjustment_date": TODAY, "lines": [{"product_id": item_id, "quantity_change": "2"}]},
    )
    assert found.status_code == 201, found.text
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 19
    assert balance_of(auth_client, "Inventory Shrinkage") == 4  # 12 - 2 x 4.00

    assert auth_client.post(f"{API}/inventory-adjustments/{shrink.json()['id']}/void").status_code == 200
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 22
    assert_books_balance(auth_client)

    history = auth_client.get(f"{API}/products/{item_id}/stock-history").json()
    assert len(history) == 5  # start, bill, -3, +2, void

    detail = auth_client.get(f"{API}/reports/inventory-valuation-detail?start_date={YEAR}-01-01&end_date={TODAY}").json()
    assert detail["summary"][0]["amount"] == f"{balance_of(auth_client, 'Inventory Asset'):.2f}"


def test_type_change_and_bundle(auth_client, stocked):
    item_id = stocked["item"]["id"]
    change = auth_client.put(f"{API}/products/{item_id}", json={"name": "Widget", "product_type": "SERVICE"})
    assert change.status_code == 422

    service = auth_client.post(f"{API}/products", json={"name": "Install", "sales_price": "5"}).json()
    bundle = auth_client.post(
        f"{API}/products",
        json={
            "name": "Widget kit",
            "product_type": "BUNDLE",
            "components": [{"product_id": item_id, "quantity": "2"}, {"product_id": service["id"], "quantity": "1"}],
        },
    )
    assert bundle.status_code == 201, bundle.text
    assert float(bundle.json()["sales_price"]) == 45  # 2 x 20 + 5
    assert len(bundle.json()["components"]) == 2

    customer = make_customer(auth_client)
    invoice = sell(auth_client, customer, bundle.json()["id"], 1, rate=90)
    assert invoice.status_code == 201, invoice.text
    lines = invoice.json()["lines"]
    assert [line["product_id"] for line in lines] == [item_id, service["id"]]
    assert [float(line["amount"]) for line in lines] == [80, 10]  # 90 shared 40:5
    assert float(get_product(auth_client, item_id)["quantity_on_hand"]) == 18
    assert balance_of(auth_client, "Cost of Goods Sold") == 8

    nested = auth_client.post(
        f"{API}/products",
        json={"name": "Big kit", "product_type": "BUNDLE", "components": [{"product_id": bundle.json()["id"], "quantity": "1"}]},
    )
    assert nested.status_code == 422


def test_categories_and_price_rules(auth_client):
    tools = auth_client.post(f"{API}/product-categories", json={"name": "Tools"}).json()
    hammer = auth_client.post(f"{API}/products", json={"name": "Hammer", "sales_price": "100", "category_id": tools["id"]}).json()
    nail = auth_client.post(f"{API}/products", json={"name": "Nail", "sales_price": "1"}).json()
    customer = make_customer(auth_client)

    auth_client.post(f"{API}/price-rules", json={"name": "Tools sale", "adjustment_percent": "-10", "category_id": tools["id"]})
    auth_client.post(
        f"{API}/price-rules",
        json={"name": "VIP hammer", "adjustment_percent": "-25", "product_id": hammer["id"], "customer_id": customer},
    )
    auth_client.post(
        f"{API}/price-rules",
        json={"name": "Old promo", "adjustment_percent": "-50", "end_date": f"{YEAR - 1}-12-31"},
    )

    def price_of(customer_id, product_id):
        query = f"?customer_id={customer_id}" if customer_id else ""
        for row in auth_client.get(f"{API}/product-prices{query}").json():
            if row["product_id"] == product_id:
                return row
        raise AssertionError(product_id)

    assert price_of(None, hammer["id"])["price"] == "90.00"
    assert price_of(customer, hammer["id"]) == {"product_id": hammer["id"], "price": "75.00", "rule_name": "VIP hammer"}
    assert price_of(None, nail["id"])["rule_name"] is None  # the promo has ended

    loop = auth_client.put(f"{API}/product-categories/{tools['id']}", json={"name": "Tools", "parent_id": tools["id"]})
    assert loop.status_code == 422


def test_import_and_export(auth_client):
    csv_text = (
        "Name,SKU,Type,Sales price,Purchase cost,Category,Quantity on hand,Reorder point\n"
        "Shovel,SH-1,Inventory,30,12,Tools,5,2\n"
        "Design,,Service,80,,,,\n"
    )
    result = auth_client.post(f"{API}/products/import", json={"content": csv_text}).json()
    assert result == {"created": 2, "updated": 0, "errors": []}

    products = {p["name"]: p for p in auth_client.get(f"{API}/products").json()}
    assert float(products["Shovel"]["quantity_on_hand"]) == 5
    assert products["Shovel"]["category"]["name"] == "Tools"
    assert products["Shovel"]["is_low_stock"] is False
    assert balance_of(auth_client, "Inventory Asset") == 60

    update = auth_client.post(f"{API}/products/import", json={"content": "Name,Sales price,Reorder point\nShovel,35,6\n"}).json()
    assert update == {"created": 0, "updated": 1, "errors": []}
    shovel = {p["name"]: p for p in auth_client.get(f"{API}/products").json()}["Shovel"]
    assert shovel["sales_price"] == "35.00"
    assert shovel["is_low_stock"] is True

    bad = auth_client.post(f"{API}/products/import", json={"content": "Name,Type\nRake,Gadget\nHoe,Service\n"}).json()
    assert bad["created"] == 0 and len(bad["errors"]) == 1
    assert "Hoe" not in {p["name"] for p in auth_client.get(f"{API}/products").json()}  # all or nothing

    exported = auth_client.get(f"{API}/products/export")
    assert exported.status_code == 200
    assert exported.text.splitlines()[0].startswith("Name,SKU,Type")
    assert "Shovel,SH-1,Inventory" in exported.text
    assert_books_balance(auth_client)
