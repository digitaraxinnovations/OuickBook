"""
Phase 8 - Classes, locations, tags, projects and budgets.
"""

from datetime import date

import pytest

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, make_customer

YEAR = date.today().year


def post(client, path, payload, expected=201):
    response = client.post(f"{API}{path}", json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def report(client, key):
    return client.get(f"{API}/reports/{key}?start_date={YEAR}-01-01&end_date={YEAR}-12-31").json()


def sections_by_title(result):
    return {section["title"]: section for section in result["sections"]}


@pytest.fixture
def setup(auth_client):
    residential = post(auth_client, "/classes", {"name": "Residential"})
    commercial = post(auth_client, "/classes", {"name": "Commercial"})
    north = post(auth_client, "/locations", {"name": "North store"})
    promo = post(auth_client, "/tags", {"name": "Spring promo", "group_name": "Campaigns"})
    customer = make_customer(auth_client)
    project = post(auth_client, "/projects", {"name": "Backyard redo", "customer_id": customer})
    return {
        "residential": residential,
        "commercial": commercial,
        "north": north,
        "promo": promo,
        "customer": customer,
        "project": project,
    }


def invoice(client, customer, amount, **tracking):
    payload = {"customer_id": customer, "invoice_date": TODAY, "lines": [{"description": "Work", "quantity": "1", "rate": str(amount)}]}
    payload.update(tracking)
    return post(client, "/invoices", payload)


def expense(client, amount, **tracking):
    payload = {
        "payment_account_id": account_id(client, "Checking"),
        "expense_date": TODAY,
        "lines": [{"account_id": account_id(client, "Repairs & Maintenance"), "amount": str(amount)}],
    }
    payload.update(tracking)
    return post(client, "/expenses", payload)


def test_tracking_on_transactions_and_reports(auth_client, setup):
    customer = setup["customer"]
    first = invoice(
        auth_client,
        customer,
        1000,
        class_id=setup["residential"]["id"],
        location_id=setup["north"]["id"],
        tag_ids=[setup["promo"]["id"]],
    )
    assert first["class_id"] == setup["residential"]["id"]
    assert first["tag_ids"] == [setup["promo"]["id"]]
    invoice(auth_client, customer, 400, class_id=setup["commercial"]["id"])
    expense(auth_client, 150, class_id=setup["residential"]["id"], location_id=setup["north"]["id"])
    invoice(auth_client, customer, 50)  # no class

    by_class = sections_by_title(report(auth_client, "profit-and-loss-by-class"))
    assert by_class["Residential - net income"]["total"] == "850.00"
    assert by_class["Commercial - net income"]["total"] == "400.00"
    assert by_class["Not specified - net income"]["total"] == "50.00"
    assert report(auth_client, "profit-and-loss-by-class")["summary"][0]["amount"] == "1300.00"

    by_location = sections_by_title(report(auth_client, "profit-and-loss-by-location"))
    assert by_location["North store - net income"]["total"] == "850.00"

    by_tag = sections_by_title(report(auth_client, "profit-and-loss-by-tag"))
    assert by_tag["Spring promo - net income"]["total"] == "1000.00"

    # Voiding keeps the tracking, so the class goes back to zero.
    auth_client.post(f"{API}/invoices/{first['id']}/void")
    by_class = sections_by_title(report(auth_client, "profit-and-loss-by-class"))
    assert by_class["Residential - net income"]["total"] == "-150.00"
    by_tag = sections_by_title(report(auth_client, "profit-and-loss-by-tag"))
    assert "Spring promo - net income" not in by_tag
    assert_books_balance(auth_client)


def test_bad_tracking_is_rejected(auth_client, setup):
    other = make_customer(auth_client, "Other Co")
    wrong_project = auth_client.post(
        f"{API}/invoices",
        json={
            "customer_id": other,
            "invoice_date": TODAY,
            "project_id": setup["project"]["id"],
            "lines": [{"description": "x", "quantity": "1", "rate": "1"}],
        },
    )
    assert wrong_project.status_code == 422
    missing_tag = auth_client.post(
        f"{API}/invoices",
        json={"customer_id": other, "invoice_date": TODAY, "tag_ids": [999], "lines": [{"description": "x", "quantity": "1", "rate": "1"}]},
    )
    assert missing_tag.status_code == 422
    duplicate = auth_client.post(f"{API}/classes", json={"name": "residential"})
    assert duplicate.status_code == 409
    loop = auth_client.put(f"{API}/classes/{setup['residential']['id']}", json={"name": "Residential", "parent_id": setup["residential"]["id"]})
    assert loop.status_code == 422


def test_manual_journal_line_tracking(auth_client, setup):
    entry = post(
        auth_client,
        "/journal-entries",
        {
            "entry_date": TODAY,
            "tag_ids": [setup["promo"]["id"]],
            "lines": [
                {"account_id": account_id(auth_client, "Advertising & Marketing"), "debit": "70", "class_id": setup["commercial"]["id"]},
                {"account_id": account_id(auth_client, "Checking"), "credit": "70"},
            ],
        },
    )
    assert entry["tag_ids"] == [setup["promo"]["id"]]
    assert entry["lines"][0]["class_id"] == setup["commercial"]["id"]
    by_class = sections_by_title(report(auth_client, "profit-and-loss-by-class"))
    assert by_class["Commercial - net income"]["total"] == "-70.00"


def test_project_profitability(auth_client, setup):
    project_id = setup["project"]["id"]
    customer = setup["customer"]
    invoice(auth_client, customer, 2000, project_id=project_id)
    vendor = auth_client.post(f"{API}/vendors", json={"display_name": "Lumber Yard"}).json()["id"]
    post(
        auth_client,
        "/purchase-documents",
        {
            "doc_type": "BILL",
            "vendor_id": vendor,
            "doc_date": TODAY,
            "project_id": project_id,
            "lines": [{"account_id": account_id(auth_client, "Repairs & Maintenance"), "quantity": "1", "rate": "600"}],
        },
    )
    employee = post(auth_client, "/employees", {"display_name": "Pat Hourly", "pay_type": "HOURLY", "pay_rate": "30"})
    post(
        auth_client,
        "/time-entries",
        {"employee_id": employee["id"], "work_date": TODAY, "hours": "10", "customer_id": customer, "project_id": project_id},
    )

    summary = auth_client.get(f"{API}/projects/{project_id}/summary").json()
    assert float(summary["income"]) == 2000
    assert float(summary["costs"]) == 600
    assert float(summary["labor_cost"]) == 300
    assert float(summary["labor_hours"]) == 10
    assert float(summary["profit"]) == 1100
    assert float(summary["margin_percent"]) == 55
    assert len(summary["transactions"]) == 2

    sections = sections_by_title(report(auth_client, "project-profitability"))
    assert sections["Backyard redo - net income"]["total"] == "1400.00"

    other = make_customer(auth_client, "Someone Else")
    wrong = auth_client.post(
        f"{API}/time-entries",
        json={"employee_id": employee["id"], "work_date": TODAY, "hours": "1", "customer_id": other, "project_id": project_id},
    )
    assert wrong.status_code == 422


def test_budget_vs_actual(auth_client, setup):
    sales = account_id(auth_client, "Sales")
    repairs = account_id(auth_client, "Repairs & Maintenance")
    monthly_sales = ["1000"] * 12
    monthly_repairs = ["100"] * 12
    budget = post(
        auth_client,
        "/budgets",
        {
            "name": f"FY{YEAR}",
            "fiscal_year": YEAR,
            "lines": [{"account_id": sales, "months": monthly_sales}, {"account_id": repairs, "months": monthly_repairs}],
        },
    )
    assert len(budget["lines"]) == 2
    assert budget["lines"][0]["months"][0] == "1000.00"

    invoice(auth_client, setup["customer"], 9000)
    expense(auth_client, 1500)

    result = auth_client.get(f"{API}/budgets/{budget['id']}/vs-actual").json()
    rows = {row["account_name"]: row for row in result["rows"]}
    assert rows["Sales"]["budget"] == "12000.00"
    assert rows["Sales"]["actual"] == "9000.00"
    assert rows["Sales"]["difference"] == "-3000.00"
    assert rows["Sales"]["percent_of_budget"] == "75.00"
    assert rows["Repairs & Maintenance"]["actual"] == "1500.00"
    assert result["budget_net_income"] == "10800.00"
    assert result["actual_net_income"] == "7500.00"

    # A budget for one class only counts that class.
    class_budget = post(
        auth_client,
        "/budgets",
        {"name": "Residential", "fiscal_year": YEAR, "class_id": setup["residential"]["id"], "lines": [{"account_id": sales, "months": monthly_sales}]},
    )
    invoice(auth_client, setup["customer"], 500, class_id=setup["residential"]["id"])
    rows = {row["account_name"]: row for row in auth_client.get(f"{API}/budgets/{class_budget['id']}/vs-actual").json()["rows"]}
    assert rows["Sales"]["actual"] == "500.00"

    bad = auth_client.post(
        f"{API}/budgets",
        json={"name": "Bad", "fiscal_year": YEAR, "lines": [{"account_id": account_id(auth_client, "Checking"), "months": monthly_sales}]},
    )
    assert bad.status_code == 422
