"""
Phase 4 - Banking: transfers, card credits, statement import (CSV / OFX),
the review queue (match, add, split, exclude, undo), bank rules,
reconciliation with reports, undo and discrepancies.
"""

from datetime import date, timedelta

import pytest

API = "/api/v1"
TODAY = date.today()


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


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


def assert_books_balance(client):
    trial = client.get(f"{API}/reports/trial-balance").json()
    assert trial["summary"][0]["amount"] == trial["summary"][1]["amount"]


def import_csv(client, account, csv_text, filename="statement.csv", **options):
    payload = {"account_id": account, "filename": filename, "content": csv_text}
    payload.update(options)
    response = client.post(f"{API}/banking/import", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def review_list(client, account, status="FOR_REVIEW"):
    return client.get(f"{API}/banking/transactions?account_id={account}&status={status}").json()


def find_line(lines, text):
    for line in lines:
        if text in line["description"]:
            return line
    raise AssertionError(text)


@pytest.fixture
def checking(auth_client):
    return account_id(auth_client, "Checking")


STATEMENT = (
    "Date,Description,Amount\n"
    f"{day(-10)},OFFICE DEPOT #123,-45.10\n"
    f"{day(-9)},CLIENT PAYMENT ACME,500.00\n"
    f"{day(-8)},TRANSFER TO SAVINGS,-200.00\n"
    f"{day(-7)},COSTCO WHOLESALE,-120.00\n"
    f"{day(-6)},MONTHLY SERVICE FEE,-12.00\n"
)


# ---------- transfers and card credits ----------

def test_transfer_and_credit_card_payment(auth_client, checking):
    savings = account_id(auth_client, "Savings")
    card = account_id(auth_client, "Credit Card")
    auth_client.post(f"{API}/banking/transfers", json={"transfer_date": day(0), "from_account_id": savings, "to_account_id": checking, "amount": "1000"})
    assert balance_of(auth_client, "Checking") == 1000
    assert balance_of(auth_client, "Savings") == -1000

    # Card charge, then pay the card from checking.
    auth_client.post(
        f"{API}/expenses",
        json={"payment_account_id": card, "expense_date": day(0), "lines": [{"account_id": account_id(auth_client, "Travel"), "amount": "300"}]},
    )
    response = auth_client.post(f"{API}/banking/transfers", json={"transfer_date": day(0), "from_account_id": checking, "to_account_id": card, "amount": "300"})
    assert response.status_code == 201, response.text
    assert balance_of(auth_client, "Credit Card") == 0
    assert balance_of(auth_client, "Checking") == 700

    assert auth_client.post(f"{API}/banking/transfers/{response.json()['id']}/void").json()["is_void"] is True
    assert balance_of(auth_client, "Credit Card") == 300
    assert_books_balance(auth_client)


def test_transfer_needs_two_different_accounts(auth_client, checking):
    response = auth_client.post(f"{API}/banking/transfers", json={"transfer_date": day(0), "from_account_id": checking, "to_account_id": checking, "amount": "5"})
    assert response.status_code == 422


def test_credit_card_credit(auth_client):
    card = account_id(auth_client, "Credit Card")
    supplies = account_id(auth_client, "Office Supplies & Software")
    auth_client.post(f"{API}/expenses", json={"payment_account_id": card, "expense_date": day(0), "lines": [{"account_id": supplies, "amount": "80"}]})
    response = auth_client.post(
        f"{API}/expenses",
        json={"kind": "CARD_CREDIT", "payment_account_id": card, "expense_date": day(0), "lines": [{"account_id": supplies, "amount": "30"}]},
    )
    assert response.status_code == 201, response.text
    assert balance_of(auth_client, "Credit Card") == 50
    assert balance_of(auth_client, "Office Supplies & Software") == 50
    assert_books_balance(auth_client)


# ---------- import ----------

def test_csv_import_skips_duplicates(auth_client, checking):
    first = import_csv(auth_client, checking, STATEMENT)
    assert first == {"imported": 5, "duplicates": 0, "auto_added": 0}
    again = import_csv(auth_client, checking, STATEMENT)
    assert again == {"imported": 0, "duplicates": 5, "auto_added": 0}
    assert len(review_list(auth_client, checking)) == 5


def test_csv_with_debit_and_credit_columns(auth_client, checking):
    text = "Posted Date,Payee,Withdrawals,Deposits\n01/15/2026,RENT,1200.00,\n01/16/2026,SALE,,350.50\n"
    result = import_csv(auth_client, checking, text)
    assert result["imported"] == 2
    lines = review_list(auth_client, checking)
    assert float(find_line(lines, "RENT")["amount"]) == -1200
    assert float(find_line(lines, "SALE")["amount"]) == 350.5


def test_ofx_import(auth_client):
    card = account_id(auth_client, "Credit Card")
    ofx = (
        "OFXHEADER:100\nDATA:OFXSGML\n<OFX><BANKTRANLIST>\n"
        "<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261101120000<TRNAMT>-64.20<FITID>A1<NAME>SHELL OIL\n</STMTTRN>\n"
        "<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261103<TRNAMT>20.00<FITID>A2<NAME>REFUND<MEMO>Returned item\n</STMTTRN>\n"
        "</BANKTRANLIST></OFX>"
    )
    result = import_csv(auth_client, card, ofx, filename="card.qfx")
    assert result["imported"] == 2
    lines = review_list(auth_client, card)
    assert find_line(lines, "SHELL")["source"] == "OFX"
    assert find_line(lines, "REFUND")["description"] == "REFUND - Returned item"
    assert import_csv(auth_client, card, ofx, filename="card.qfx")["duplicates"] == 2


def test_bank_feed_is_not_connected(auth_client, checking):
    response = auth_client.post(f"{API}/banking/accounts/{checking}/sync")
    assert response.status_code == 422
    assert "BANK_FEED_PROVIDER" in response.json()["detail"]


# ---------- review: add, split, transfer, exclude, undo ----------

def test_add_expense_deposit_transfer_from_bank_lines(auth_client, checking):
    import_csv(auth_client, checking, STATEMENT)
    lines = review_list(auth_client, checking)

    office = find_line(lines, "OFFICE DEPOT")
    response = auth_client.post(
        f"{API}/banking/transactions/{office['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Office Supplies & Software"), "amount": "45.10"}]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["added_as"] == "EXPENSE"

    payment = find_line(lines, "CLIENT PAYMENT")
    response = auth_client.post(
        f"{API}/banking/transactions/{payment['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Sales"), "amount": "500"}]},
    )
    assert response.json()["added_as"] == "DEPOSIT"

    transfer = find_line(lines, "TRANSFER TO SAVINGS")
    response = auth_client.post(
        f"{API}/banking/transactions/{transfer['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Savings"), "amount": "200"}]},
    )
    assert response.json()["added_as"] == "TRANSFER"

    # Split: 120 at Costco = 90 supplies + 30 meals
    costco = find_line(lines, "COSTCO")
    bad_split = auth_client.post(
        f"{API}/banking/transactions/{costco['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Office Supplies & Software"), "amount": "90"}]},
    )
    assert bad_split.status_code == 422
    response = auth_client.post(
        f"{API}/banking/transactions/{costco['id']}/add",
        json={
            "lines": [
                {"account_id": account_id(auth_client, "Office Supplies & Software"), "amount": "90"},
                {"account_id": account_id(auth_client, "Meals & Entertainment"), "amount": "30"},
            ]
        },
    )
    assert response.status_code == 200, response.text

    fee = find_line(lines, "SERVICE FEE")
    assert auth_client.post(f"{API}/banking/transactions/{fee['id']}/exclude").json()["status"] == "EXCLUDED"

    assert review_list(auth_client, checking) == []
    # Book balance = 500 - 45.10 - 200 - 120 = 134.90 (the excluded fee is not in the books)
    assert balance_of(auth_client, "Checking") == 134.9
    assert balance_of(auth_client, "Savings") == 200
    assert_books_balance(auth_client)

    # Undo the expense: it is voided and the line goes back to review.
    undone = auth_client.post(f"{API}/banking/transactions/{office['id']}/undo").json()
    assert undone["status"] == "FOR_REVIEW"
    assert balance_of(auth_client, "Office Supplies & Software") == 90
    assert auth_client.post(f"{API}/banking/transactions/{fee['id']}/undo").json()["status"] == "FOR_REVIEW"
    assert_books_balance(auth_client)


def test_card_payment_and_refund_from_card_lines(auth_client, checking):
    card = account_id(auth_client, "Credit Card")
    text = f"Date,Description,Amount\n{day(-3)},PAYMENT THANK YOU,250.00\n{day(-2)},AMAZON REFUND,15.00\n"
    import_csv(auth_client, card, text)
    lines = review_list(auth_client, card)

    payment = find_line(lines, "PAYMENT THANK YOU")
    result = auth_client.post(f"{API}/banking/transactions/{payment['id']}/add", json={"lines": [{"account_id": checking, "amount": "250"}]}).json()
    assert result["added_as"] == "TRANSFER"
    assert balance_of(auth_client, "Checking") == -250

    refund = find_line(lines, "AMAZON REFUND")
    result = auth_client.post(
        f"{API}/banking/transactions/{refund['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Office Supplies & Software"), "amount": "15"}]},
    ).json()
    assert result["added_as"] == "CARD_CREDIT"
    assert balance_of(auth_client, "Credit Card") == -265  # you are owed by the card
    assert_books_balance(auth_client)


def test_match_existing_payment(auth_client, checking):
    # A customer payment already recorded in the books...
    customer = auth_client.post(f"{API}/customers", json={"display_name": "Acme"}).json()["id"]
    invoice = auth_client.post(
        f"{API}/invoices",
        json={"customer_id": customer, "invoice_date": day(-12), "lines": [{"description": "Work", "quantity": "1", "rate": "500"}]},
    ).json()
    auth_client.post(
        f"{API}/payments",
        json={
            "customer_id": customer,
            "payment_date": day(-9),
            "amount": "500",
            "deposit_account_id": checking,
            "applications": [{"invoice_id": invoice["id"], "amount": "500"}],
        },
    )
    # ...shows up on the bank statement.
    import_csv(auth_client, checking, STATEMENT)
    bank_line = find_line(review_list(auth_client, checking), "CLIENT PAYMENT")
    matches = auth_client.get(f"{API}/banking/transactions/{bank_line['id']}/matches").json()
    assert len(matches) == 1 and float(matches[0]["amount"]) == 500

    result = auth_client.post(f"{API}/banking/transactions/{bank_line['id']}/match", json={"journal_line_id": matches[0]["journal_line_id"]})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "MATCHED"
    assert balance_of(auth_client, "Checking") == 500  # nothing new was posted

    # A matched line cannot be matched again.
    assert auth_client.get(f"{API}/banking/transactions/{bank_line['id']}/matches").json() == []


# ---------- rules ----------

def test_bank_rules_suggest_and_auto_add(auth_client, checking):
    supplies = account_id(auth_client, "Office Supplies & Software")
    fees = account_id(auth_client, "Bank Charges & Fees")
    auth_client.post(
        f"{API}/banking/rules",
        json={"name": "Office stores", "direction": "MONEY_OUT", "match_type": "ANY",
              "conditions": [{"field": "description", "operator": "contains", "value": "office depot"},
                             {"field": "description", "operator": "contains", "value": "staples"}],
              "category_account_id": supplies},
    )
    auth_client.post(
        f"{API}/banking/rules",
        json={"name": "Bank fees", "direction": "MONEY_OUT",
              "conditions": [{"field": "description", "operator": "contains", "value": "service fee"},
                             {"field": "amount", "operator": "less_than", "value": "50"}],
              "category_account_id": fees, "auto_add": True},
    )
    result = import_csv(auth_client, checking, STATEMENT)
    assert result["auto_added"] == 1
    assert balance_of(auth_client, "Bank Charges & Fees") == 12

    waiting = review_list(auth_client, checking)
    assert len(waiting) == 4
    office = find_line(waiting, "OFFICE DEPOT")
    assert office["suggested_account"]["id"] == supplies
    assert find_line(waiting, "COSTCO")["suggested_account"] is None


# ---------- reconciliation ----------

def test_reconcile_undo_and_discrepancy(auth_client, checking):
    import_csv(auth_client, checking, STATEMENT)
    lines = review_list(auth_client, checking)
    payment = find_line(lines, "CLIENT PAYMENT")
    office = find_line(lines, "OFFICE DEPOT")
    auth_client.post(f"{API}/banking/transactions/{payment['id']}/add", json={"lines": [{"account_id": account_id(auth_client, "Sales"), "amount": "500"}]})
    auth_client.post(
        f"{API}/banking/transactions/{office['id']}/add",
        json={"lines": [{"account_id": account_id(auth_client, "Office Supplies & Software"), "amount": "45.10"}]},
    )
    # A check written in the books that has not cleared the bank yet.
    auth_client.post(
        f"{API}/expenses",
        json={"kind": "CHECK", "payment_account_id": checking, "expense_date": day(-5), "lines": [{"account_id": account_id(auth_client, "Travel"), "amount": "60"}]},
    )

    started = auth_client.post(f"{API}/banking/reconciliations", json={"account_id": checking, "statement_date": day(0), "ending_balance": "454.90"})
    assert started.status_code == 201, started.text
    rec_id = started.json()["id"]

    workspace = auth_client.get(f"{API}/banking/reconciliations/{rec_id}").json()
    assert len(workspace["items"]) == 3
    # Lines that came from the bank start ticked: 500 - 45.10 = 454.90
    assert float(workspace["cleared_balance"]) == 454.9
    assert float(workspace["difference"]) == 0

    # Ticking the uncleared check makes it unbalanced, so finishing is refused.
    all_ids = [item["journal_line_id"] for item in workspace["items"]]
    unbalanced = auth_client.put(f"{API}/banking/reconciliations/{rec_id}/selection", json={"journal_line_ids": all_ids}).json()
    assert float(unbalanced["difference"]) == 60
    assert auth_client.post(f"{API}/banking/reconciliations/{rec_id}/finish").status_code == 422

    cleared_ids = [item["journal_line_id"] for item in workspace["items"] if item["selected"]]
    auth_client.put(f"{API}/banking/reconciliations/{rec_id}/selection", json={"journal_line_ids": cleared_ids})
    finished = auth_client.post(f"{API}/banking/reconciliations/{rec_id}/finish")
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == "COMPLETED"

    report = auth_client.get(f"{API}/banking/reconciliations/{rec_id}/report").json()
    assert len(report["cleared_increases"]) == 1 and len(report["cleared_decreases"]) == 1
    assert len(report["uncleared"]) == 1 and float(report["uncleared"][0]["amount"]) == -60
    assert float(report["register_balance"]) == 394.9

    overview = auth_client.get(f"{API}/banking/accounts").json()
    assert [item for item in overview if item["account"]["id"] == checking][0]["last_reconciled"] == day(0)

    # Undoing a reconciled bank line is blocked until the reconciliation is undone.
    assert auth_client.post(f"{API}/banking/transactions/{office['id']}/undo").status_code == 422

    # Voiding a reconciled expense shows up as a discrepancy.
    expense_id = auth_client.get(f"{API}/banking/transactions?account_id={checking}&status=ADDED").json()
    office_added = [item for item in expense_id if "OFFICE" in item["description"]][0]
    auth_client.post(f"{API}/expenses/{office_added['added_id']}/void")
    discrepancies = auth_client.get(f"{API}/banking/reconciliations/discrepancies?account_id={checking}").json()
    assert len(discrepancies) == 1 and float(discrepancies[0]["amount"]) == -45.1

    # A second reconciliation starts from the first one's ending balance.
    second = auth_client.post(f"{API}/banking/reconciliations", json={"account_id": checking, "statement_date": day(1), "ending_balance": "394.90"}).json()
    assert float(second["beginning_balance"]) == 454.9
    auth_client.delete(f"{API}/banking/reconciliations/{second['id']}")

    undone = auth_client.post(f"{API}/banking/reconciliations/{rec_id}/undo")
    assert undone.json()["status"] == "UNDONE"
    assert_books_balance(auth_client)


def test_cannot_reconcile_a_non_bank_account(auth_client):
    response = auth_client.post(
        f"{API}/banking/reconciliations",
        json={"account_id": account_id(auth_client, "Sales"), "statement_date": day(0), "ending_balance": "0"},
    )
    assert response.status_code == 422
