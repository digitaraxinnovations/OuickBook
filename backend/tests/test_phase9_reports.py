"""
Phase 9 - Reports: cash vs accrual, columns, comparisons, statements,
receivables / payables, sales and expense summaries, exports, saved reports
and scheduled emails. Also runs every report in every format.
"""

from datetime import date

import pytest

from tests.test_phase2_sales import API, TODAY, account_id, balance_of, make_customer

YEAR = date.today().year
PERIOD = f"start_date={YEAR}-01-01&end_date={YEAR}-12-31"


def post(client, path, payload, expected=201):
    response = client.post(f"{API}{path}", json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def run(client, key, query=""):
    response = client.get(f"{API}/reports/{key}?{PERIOD}{('&' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def summary(result):
    return {row["label"]: row for row in result["summary"]}


def section(result, title):
    for item in result["sections"]:
        if item["title"] == title:
            return item
    raise AssertionError(title)


@pytest.fixture
def books(auth_client):
    """
    Invoice 1000 (400 paid), sales receipt 200, expense 150,
    bill 300 (100 paid) - all to one customer / one vendor.
    """
    customer = make_customer(auth_client, "Rex Retail")
    vendor = post(auth_client, "/vendors", {"display_name": "Valley Supply"})["id"]
    checking = account_id(auth_client, "Checking")
    supplies = account_id(auth_client, "Office Supplies & Software")
    line = [{"description": "Work", "quantity": "1", "rate": "1000"}]

    invoice = post(auth_client, "/invoices", {"customer_id": customer, "invoice_date": TODAY, "lines": line})
    post(
        auth_client,
        "/payments",
        {"customer_id": customer, "payment_date": TODAY, "amount": "400", "applications": [{"invoice_id": invoice["id"], "amount": "400"}]},
    )
    post(
        auth_client,
        "/sales-documents",
        {"doc_type": "SALES_RECEIPT", "customer_id": customer, "doc_date": TODAY, "lines": [{"description": "Cash sale", "quantity": "1", "rate": "200"}]},
    )
    post(
        auth_client,
        "/expenses",
        {"vendor_id": vendor, "payment_account_id": checking, "expense_date": TODAY, "lines": [{"account_id": supplies, "amount": "150"}]},
    )
    bill = post(
        auth_client,
        "/purchase-documents",
        {"doc_type": "BILL", "vendor_id": vendor, "doc_date": TODAY, "doc_number": "B-77", "lines": [{"account_id": supplies, "quantity": "1", "rate": "300"}]},
    )
    post(
        auth_client,
        "/bill-payments",
        {"vendor_id": vendor, "payment_date": TODAY, "payment_account_id": checking, "applications": [{"bill_id": bill["id"], "amount": "100"}]},
    )
    return {"customer": customer, "vendor": vendor, "checking": checking}


def test_profit_and_loss_accrual_and_cash(auth_client, books):
    accrual = run(auth_client, "profit-and-loss")
    assert section(accrual, "Income")["total"] == "1200.00"
    assert section(accrual, "Expenses")["total"] == "450.00"
    assert summary(accrual)["Net income"]["amount"] == "750.00"

    cash = run(auth_client, "profit-and-loss", "basis=cash")
    assert cash["basis"] == "cash"
    assert section(cash, "Income")["total"] == "600.00"  # 400 paid + 200 sales receipt
    assert section(cash, "Expenses")["total"] == "250.00"  # 150 expense + 100 paid on the bill
    assert summary(cash)["Net income"]["amount"] == "350.00"

    by_customer = run(auth_client, "profit-and-loss", f"customer_id={books['customer']}")
    assert summary(by_customer)["Net income"]["amount"] == "1200.00"


def test_profit_and_loss_columns_and_comparison(auth_client, books):
    by_month = run(auth_client, "profit-and-loss-by-month")
    assert by_month["columns"][0] == f"Jan {YEAR}"
    assert by_month["columns"][-1] == "Total"
    assert len(by_month["columns"]) == 13
    net = summary(by_month)["Net income"]
    month_index = date.today().month - 1
    assert net["values"][month_index] == "750.00"
    assert net["values"][-1] == "750.00"

    by_customer = run(auth_client, "profit-and-loss-by-customer")
    assert "Rex Retail" in by_customer["columns"]
    income = section(by_customer, "Income")
    assert income["totals"][by_customer["columns"].index("Rex Retail")] == "1200.00"

    comparison = run(auth_client, "profit-and-loss-comparison")
    assert comparison["columns"][2:] == ["$ change", "% change"]
    assert comparison["column_kinds"] == ["money", "money", "money", "percent"]
    net = summary(comparison)["Net income"]["values"]
    assert net[0] == "750.00" and net[1] == "0.00" and net[2] == "750.00" and net[3] is None


def test_statements_tie_out(auth_client, books):
    sheet = run(auth_client, "balance-sheet-comparison")
    totals = summary(sheet)
    assert totals["Total assets"]["values"][0] == totals["Total liabilities and equity"]["values"][0]
    assert totals["Total assets"]["values"][1] == totals["Total liabilities and equity"]["values"][1]

    flow = run(auth_client, "cash-flow")
    cash_now = balance_of(auth_client, "Checking") + balance_of(auth_client, "Undeposited Funds")
    assert float(summary(flow)["Cash at end of period"]["amount"]) == cash_now
    operating = section(flow, "Operating activities")
    assert operating["rows"][0]["label"] == "Net income"

    ledger = run(auth_client, "general-ledger")
    checking = section(ledger, "Checking")
    assert float(checking["rows"][-1]["values"][1]) == balance_of(auth_client, "Checking")
    assert ledger["text_columns"] == ["Date", "Type", "Num", "Name", "Memo"]
    bill_payment = [row for row in checking["rows"] if row["cells"][1] == "Bill Payment"][0]
    assert bill_payment["cells"][3] == "Valley Supply"

    quick = run(auth_client, "account-quickreport", f"account_id={books['checking']}")
    assert [item["title"] for item in quick["sections"]] == ["Checking"]
    assert run(auth_client, "account-quickreport")["notes"] == ["Choose an account."]

    journal = run(auth_client, "journal")
    total = summary(journal)["Total"]["values"]
    assert total[0] == total[1]

    vendor_list = run(auth_client, "transaction-list", f"vendor_id={books['vendor']}")
    types = sorted(row["cells"][1] for row in vendor_list["sections"][0]["rows"])
    assert types == ["Bill", "Bill Payment", "Expense"]
    bill_row = [row for row in vendor_list["sections"][0]["rows"] if row["cells"][1] == "Bill"][0]
    assert bill_row["cells"][2] == "B-77"


def test_receivables_and_payables(auth_client, books):
    ar_summary = run(auth_client, "ar-aging-summary")
    assert ar_summary["columns"][-1] == "Total"
    assert summary(ar_summary)["Total"]["amount"] == "600.00"
    assert run(auth_client, "ar-aging")["summary"][0]["amount"] == "600.00"
    assert summary(run(auth_client, "open-invoices"))["Total"]["amount"] == "600.00"
    today = auth_client.get(f"{API}/reports/collections?end_date={TODAY}").json()
    assert today["sections"] == []  # nothing overdue yet
    year_end = run(auth_client, "collections")  # by Dec 31 the invoice is overdue
    assert section(year_end, "Rex Retail")["total"] == "600.00"
    assert summary(run(auth_client, "customer-balance-summary"))["Total"]["amount"] == "600.00"

    assert summary(run(auth_client, "ap-aging-summary"))["Total"]["amount"] == "200.00"
    assert summary(run(auth_client, "unpaid-bills"))["Total"]["amount"] == "200.00"
    assert summary(run(auth_client, "vendor-balance-summary"))["Total"]["amount"] == "200.00"
    assert section(run(auth_client, "vendor-balance-detail"), "Valley Supply")["total"] == "200.00"


def test_sales_and_expense_summaries(auth_client, books):
    sales = run(auth_client, "sales-by-customer")
    assert sales["sections"][0]["rows"][0] == {"label": "Rex Retail", "amount": "1200.00", "account_id": None, "cells": [], "values": []}
    assert run(auth_client, "sales-by-customer", "basis=cash")["sections"][0]["rows"][0]["amount"] == "600.00"

    products = run(auth_client, "sales-by-product")
    assert products["column_kinds"] == ["number", "money", "money"]
    row = products["sections"][0]["rows"][0]
    assert row["values"][0] == "2.00" and row["values"][1] == "1200.00"

    expenses = run(auth_client, "expenses-by-vendor")
    assert expenses["sections"][0]["rows"][0]["amount"] == "450.00"


def test_every_report_runs_and_exports(auth_client, books):
    reports = auth_client.get(f"{API}/reports").json()
    assert len(reports) >= 37
    assert reports[0]["group"] == "Business overview"
    for info in reports:
        run(auth_client, info["key"])
        for file_format in ("pdf", "csv", "xlsx"):
            response = auth_client.get(f"{API}/reports/{info['key']}/export?file_format={file_format}&{PERIOD}")
            assert response.status_code == 200, (info["key"], file_format, response.text)
    xlsx = auth_client.get(f"{API}/reports/profit-and-loss-by-month/export?file_format=xlsx&{PERIOD}")
    assert xlsx.content[:2] == b"PK"
    csv_text = auth_client.get(f"{API}/reports/profit-and-loss/export?file_format=csv&{PERIOD}").content.decode("utf-8-sig")
    assert "Net income" in csv_text and "750.00" in csv_text
    assert auth_client.get(f"{API}/reports/profit-and-loss/export?file_format=doc").status_code == 422


def test_saved_reports_and_schedules(auth_client, books):
    saved = post(
        auth_client,
        "/saved-reports",
        {"name": "Cash P&L", "report_key": "profit-and-loss", "date_range": "this_year", "options": {"basis": "cash"}},
    )
    assert saved["options"]["basis"] == "cash"
    result = auth_client.get(f"{API}/saved-reports/{saved['id']}/run").json()
    assert summary(result)["Net income"]["amount"] == "350.00"
    assert result["title"] == "Cash P&L (Profit and Loss)"

    schedule = post(
        auth_client,
        "/report-schedules",
        {"saved_report_id": saved["id"], "frequency": "WEEKLY", "next_send_date": TODAY, "recipients": ["owner@example.com"], "file_format": "xlsx"},
    )
    sent = post(auth_client, "/report-schedules/send-due", {}, expected=200)
    assert sent == {"sent": 1}
    schedules = auth_client.get(f"{API}/report-schedules").json()
    assert schedules[0]["last_sent_at"] == TODAY
    assert schedules[0]["next_send_date"] > TODAY
    assert post(auth_client, "/report-schedules/send-due", {}, expected=200) == {"sent": 0}

    bad = auth_client.post(
        f"{API}/report-schedules",
        json={"saved_report_id": saved["id"], "frequency": "WEEKLY", "next_send_date": TODAY, "recipients": ["nobody"]},
    )
    assert bad.status_code == 422
    assert auth_client.delete(f"{API}/saved-reports/{saved['id']}").status_code == 204
    assert auth_client.get(f"{API}/report-schedules").json() == []
    assert schedule["id"]
