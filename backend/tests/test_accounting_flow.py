"""
End-to-end accounting checks: invoice -> payment -> expense -> reports.
"""

API = "/api/v1"


def find_account_id(client, name):
    for account in client.get(f"{API}/accounts").json():
        if account["name"] == name:
            return account["id"]
    raise AssertionError(f"Account {name} not found")


def find_row(report, section_title, label):
    for section in report["sections"]:
        if section["title"] == section_title:
            for row in section["rows"]:
                if row["label"] == label:
                    return float(row["amount"])
    return None


def create_customer(client):
    response = client.post(f"{API}/customers", json={"display_name": "Acme Corp", "email": ""})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_invoice(client, customer_id):
    response = client.post(
        f"{API}/invoices",
        json={
            "customer_id": customer_id,
            "invoice_date": "2026-11-01",
            "lines": [
                {"description": "Website design", "quantity": "2", "rate": "500"},
                {"description": "Hosting", "quantity": "1", "rate": "100"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invoice_records_income_and_receivable(auth_client):
    invoice = create_invoice(auth_client, create_customer(auth_client))

    assert invoice["invoice_number"] == "1001"
    assert float(invoice["total"]) == 1100
    assert invoice["due_date"] == "2026-12-01"  # 30-day default terms

    report = auth_client.get(f"{API}/reports/profit-and-loss?start_date=2026-01-01&end_date=2026-12-31").json()
    assert find_row(report, "Income", "Sales") == 1100

    sheet = auth_client.get(f"{API}/reports/balance-sheet?end_date=2026-12-31").json()
    assert find_row(sheet, "Assets", "Accounts Receivable (A/R)") == 1100


def test_payment_moves_money_from_receivable_to_bank(auth_client):
    invoice = create_invoice(auth_client, create_customer(auth_client))
    checking_id = find_account_id(auth_client, "Checking")

    customer_id = invoice["customer"]["id"]
    response = auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer_id,
            "payment_date": "2026-11-10",
            "amount": "600",
            "deposit_account_id": checking_id,
            "applications": [{"invoice_id": invoice["id"], "amount": "600"}],
        },
    )
    assert response.status_code == 201, response.text

    updated = auth_client.get(f"{API}/invoices/{invoice['id']}").json()
    assert updated["status"] == "PARTIALLY_PAID"
    assert float(updated["balance_due"]) == 500

    too_much = auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer_id,
            "payment_date": "2026-11-11",
            "amount": "900",
            "applications": [{"invoice_id": invoice["id"], "amount": "900"}],
        },
    )
    assert too_much.status_code == 422

    sheet = auth_client.get(f"{API}/reports/balance-sheet?end_date=2026-12-31").json()
    assert find_row(sheet, "Assets", "Checking") == 600
    assert find_row(sheet, "Assets", "Accounts Receivable (A/R)") == 500


def test_expense_reduces_profit_and_books_stay_balanced(auth_client):
    create_invoice(auth_client, create_customer(auth_client))
    response = auth_client.post(
        f"{API}/expenses",
        json={
            "payment_account_id": find_account_id(auth_client, "Credit Card"),
            "expense_date": "2026-11-05",
            "lines": [{"account_id": find_account_id(auth_client, "Rent & Lease"), "amount": "300"}],
        },
    )
    assert response.status_code == 201, response.text

    report = auth_client.get(f"{API}/reports/profit-and-loss?start_date=2026-01-01&end_date=2026-12-31").json()
    assert float(report["summary"][-1]["amount"]) == 800  # 1100 income - 300 rent

    trial = auth_client.get(f"{API}/reports/trial-balance?end_date=2026-12-31").json()
    total_debits = float(trial["summary"][0]["amount"])
    total_credits = float(trial["summary"][1]["amount"])
    assert total_debits == total_credits

    sheet = auth_client.get(f"{API}/reports/balance-sheet?end_date=2026-12-31").json()
    assert sheet["summary"][0]["amount"] == sheet["summary"][1]["amount"]


def test_void_invoice_reverses_income(auth_client):
    invoice = create_invoice(auth_client, create_customer(auth_client))
    response = auth_client.post(f"{API}/invoices/{invoice['id']}/void")
    assert response.status_code == 200
    assert response.json()["status"] == "VOID"

    report = auth_client.get(f"{API}/reports/profit-and-loss?start_date=2026-01-01&end_date=2026-12-31").json()
    assert float(report["summary"][-1]["amount"]) == 0


def test_unbalanced_manual_journal_is_rejected(auth_client):
    response = auth_client.post(
        f"{API}/journal-entries",
        json={
            "entry_date": "2026-11-01",
            "lines": [
                {"account_id": find_account_id(auth_client, "Checking"), "debit": "100"},
                {"account_id": find_account_id(auth_client, "Owner's Investment"), "credit": "90"},
            ],
        },
    )
    assert response.status_code == 422
    assert "must be equal" in response.json()["detail"]
