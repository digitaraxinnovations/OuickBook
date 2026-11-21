"""
Phase 10 - Companies, users, roles, invitations, audit log, settings
(closing date), multi-currency, search, recent transactions, import/export.
"""

from datetime import date, timedelta

from tests.test_phase2_sales import API, TODAY, account_id, assert_books_balance, balance_of, make_customer

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
LAST_WEEK = (date.today() - timedelta(days=7)).isoformat()


def post(client, path, payload, expected=201):
    response = client.post(f"{API}{path}", json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def invoice_payload(customer, amount=100, invoice_date=TODAY, **extra):
    payload = {"customer_id": customer, "invoice_date": invoice_date, "lines": [{"description": "Work", "quantity": "1", "rate": str(amount)}]}
    payload.update(extra)
    return payload


def latest_invitation_token(client):
    """The invite link is in the email log (EMAIL_PROVIDER=log)."""
    emails = client.get(f"{API}/email-log").json()
    body = [email for email in emails if "accept-invite" in email["body"]][0]["body"]
    return body.split("token=")[1].split()[0]


def test_invite_roles_and_permissions(auth_client):
    owner_header = auth_client.headers["Authorization"]
    customer = make_customer(auth_client)
    post(auth_client, "/invitations", {"email": "sales@example.com", "role": "SALES"})
    token = latest_invitation_token(auth_client)

    info = auth_client.get(f"{API}/auth/invitations/{token}").json()
    assert info["company_name"] == "Test Company" and info["has_account"] is False
    accepted = post(auth_client, f"/auth/invitations/{token}/accept", {"full_name": "Sam Seller", "password": "sales-password"}, expected=200)
    auth_client.headers["Authorization"] = "Bearer " + accepted["access_token"]

    me = auth_client.get(f"{API}/auth/me").json()
    assert me["role"] == "SALES" and me["company"]["name"] == "Test Company"
    assert auth_client.get(f"{API}/invoices").status_code == 200
    post(auth_client, "/invoices", invoice_payload(customer))
    assert auth_client.get(f"{API}/accounts").status_code == 200  # forms need the account list
    blocked = auth_client.post(f"{API}/expenses", json={"payment_account_id": 1, "expense_date": TODAY, "lines": [{"account_id": 1, "amount": "1"}]})
    assert blocked.status_code == 403
    assert auth_client.get(f"{API}/users").status_code == 403
    assert auth_client.get(f"{API}/reports/profit-and-loss").status_code == 403

    # The owner makes them reports-only.
    auth_client.headers["Authorization"] = owner_header
    users = auth_client.get(f"{API}/users").json()
    seller = [item for item in users if item["email"] == "sales@example.com"][0]
    owner = [item for item in users if item["is_primary_admin"]][0]
    auth_client.put(f"{API}/users/{seller['user_id']}", json={"role": "REPORTS_ONLY"})
    demote_owner = auth_client.put(f"{API}/users/{owner['user_id']}", json={"role": "STANDARD"})
    assert demote_owner.status_code == 422

    auth_client.headers["Authorization"] = "Bearer " + accepted["access_token"]
    assert auth_client.get(f"{API}/reports/profit-and-loss").status_code == 200
    assert auth_client.post(f"{API}/invoices", json=invoice_payload(customer)).status_code == 403

    # Used invitations cannot be used again.
    assert auth_client.get(f"{API}/auth/invitations/{token}").status_code == 404


def test_several_companies_and_switching(auth_client):
    make_customer(auth_client, "First Co Customer")
    companies = post(auth_client, "/companies", {"name": "Second Company"})
    current = [item for item in companies if item["is_current"]][0]
    assert current["company_name"] == "Second Company" and current["role"] == "ADMIN"
    assert auth_client.get(f"{API}/customers").json() == []  # nothing from the first company
    assert balance_of(auth_client, "Checking") == 0

    first = [item for item in companies if item["company_name"] == "Test Company"][0]
    post(auth_client, f"/companies/{first['company_id']}/switch", {}, expected=200)
    assert [item["display_name"] for item in auth_client.get(f"{API}/customers").json()] == ["First Co Customer"]
    assert auth_client.post(f"{API}/companies/999999/switch").status_code == 404


def test_audit_log(auth_client):
    customer = make_customer(auth_client, "Audit Me")
    auth_client.put(f"{API}/customers/{customer}", json={"display_name": "Audit Me", "phone": "555-0100"})
    post(auth_client, "/invoices", invoice_payload(customer))
    log = auth_client.get(f"{API}/audit-log").json()
    summaries = [entry["summary"] for entry in log]
    assert "Added customer Audit Me" in summaries
    changed = [entry for entry in log if entry["action"] == "CHANGED" and entry["entity_type"] == "Customer"][0]
    assert changed["changes"]["phone"] == [None, "555-0100"]
    assert changed["user_name"] == "Test Owner"
    assert any(entry["entity_type"] == "Invoice" and entry["action"] == "CREATED" for entry in log)
    only_invoices = auth_client.get(f"{API}/audit-log?entity_type=Invoice").json()
    assert all(entry["entity_type"] == "Invoice" for entry in only_invoices)


def test_closing_date_and_password(auth_client):
    customer = make_customer(auth_client)
    settings = auth_client.get(f"{API}/company/advanced-settings").json()
    settings.update({"closing_date": YESTERDAY, "closing_password": "close-it"})
    saved = auth_client.put(f"{API}/company/advanced-settings", json=settings).json()
    assert saved["has_closing_password"] is True

    blocked = auth_client.post(f"{API}/invoices", json=invoice_payload(customer, invoice_date=LAST_WEEK))
    assert blocked.status_code == 422 and blocked.json()["code"] == "BOOKS_CLOSED"
    wrong = auth_client.post(f"{API}/invoices", json=invoice_payload(customer, invoice_date=LAST_WEEK), headers={"X-Closing-Password": "nope"})
    assert wrong.status_code == 422
    allowed = auth_client.post(f"{API}/invoices", json=invoice_payload(customer, invoice_date=LAST_WEEK), headers={"X-Closing-Password": "close-it"})
    assert allowed.status_code == 201
    assert auth_client.post(f"{API}/invoices", json=invoice_payload(customer)).status_code == 201  # today is open


def test_accounting_method_and_fiscal_year_defaults(auth_client):
    settings = auth_client.get(f"{API}/company/advanced-settings").json()
    settings.update({"accounting_method": "CASH", "fiscal_year_start_month": 4})
    auth_client.put(f"{API}/company/advanced-settings", json=settings)
    report = auth_client.get(f"{API}/reports/profit-and-loss?end_date={TODAY}").json()
    assert report["basis"] == "cash"
    today = date.today()
    expected_year = today.year if today.month >= 4 else today.year - 1
    assert report["start_date"] == f"{expected_year}-04-01"
    assert auth_client.get(f"{API}/reports/profit-and-loss?basis=accrual").json()["basis"] == "accrual"


def test_multicurrency_invoice_and_payment(auth_client):
    assert auth_client.post(f"{API}/currencies", json={"code": "EUR", "name": "Euro"}).status_code == 422  # not turned on
    settings = auth_client.get(f"{API}/company/advanced-settings").json()
    settings["multicurrency_enabled"] = True
    auth_client.put(f"{API}/company/advanced-settings", json=settings)
    post(auth_client, "/currencies", {"code": "EUR", "name": "Euro"})
    assert auth_client.post(f"{API}/currencies", json={"code": "USD", "name": "Home"}).status_code == 422

    customer = make_customer(auth_client, "Euro Client", currency_code="EUR")
    no_rate = auth_client.post(f"{API}/invoices", json=invoice_payload(customer))
    assert no_rate.status_code == 422
    post(auth_client, "/exchange-rates", {"currency_code": "EUR", "rate_date": YESTERDAY, "rate": "1.10"})

    invoice = post(auth_client, "/invoices", invoice_payload(customer, 100))
    assert invoice["currency_code"] == "EUR" and float(invoice["exchange_rate"]) == 1.1
    assert balance_of(auth_client, "Accounts Receivable (A/R)") == 110

    payment = post(
        auth_client,
        "/payments",
        {
            "customer_id": customer,
            "payment_date": TODAY,
            "amount": "100",
            "exchange_rate": "1.20",
            "deposit_account_id": account_id(auth_client, "Checking"),
            "applications": [{"invoice_id": invoice["id"], "amount": "100"}],
        },
    )
    assert payment["currency_code"] == "EUR"
    assert balance_of(auth_client, "Checking") == 120
    assert balance_of(auth_client, "Accounts Receivable (A/R)") == 0
    assert balance_of(auth_client, "Exchange Gain or Loss") == -10  # a gain (credit to the account)
    assert_books_balance(auth_client)

    change = auth_client.put(f"{API}/customers/{customer}", json={"display_name": "Euro Client", "currency_code": None})
    assert change.status_code == 422
    refresh = auth_client.post(f"{API}/exchange-rates/refresh")
    assert refresh.status_code == 422  # no rates service connected (EXT)


def test_search_and_recent(auth_client):
    customer = make_customer(auth_client, "Zebra Landscaping")
    post(auth_client, "/invoices", invoice_payload(customer, 432.10))
    results = auth_client.get(f"{API}/search?q=zebra").json()
    assert results[0]["kind"] == "Customer" and results[0]["href"] == f"/sales/customers/{customer}"
    by_amount = auth_client.get(f"{API}/search?q=432.10").json()
    assert any(item["kind"] == "Invoice" for item in by_amount)
    assert auth_client.get(f"{API}/search?q=z").json() == []

    recent = auth_client.get(f"{API}/recent").json()
    assert recent[0]["type_label"] == "Invoice"
    assert recent[0]["name"] == "Zebra Landscaping"
    assert recent[0]["href"].startswith("/sales/invoices/")


def test_import_and_export(auth_client):
    customers_csv = "Name,Email,Phone\nAlpha Ltd,a@alpha.example.com,111\nBeta LLC,,222\n"
    result = post(auth_client, "/data/customers/import", {"content": customers_csv}, expected=200)
    assert result == {"created": 2, "updated": 0, "errors": []}
    again = post(auth_client, "/data/customers/import", {"content": "Name,Phone\nAlpha Ltd,999\n"}, expected=200)
    assert again["updated"] == 1
    exported = auth_client.get(f"{API}/data/customers/export").text
    assert "Alpha Ltd" in exported and "999" in exported

    accounts_csv = "Number,Name,Type,Detail type,Parent\n6410,Postage,EXPENSE,Office,Office Supplies & Software\n"
    assert post(auth_client, "/data/accounts/import", {"content": accounts_csv}, expected=200)["created"] == 1
    postage = [item for item in auth_client.get(f"{API}/accounts").json() if item["name"] == "Postage"][0]
    assert postage["full_name"] == "Office Supplies & Software:Postage"

    journal_csv = (
        "Entry no,Date,Account,Debit,Credit,Memo\n"
        f"1,{TODAY},Postage,25,,Stamps\n"
        f"1,{TODAY},Checking,,25,Stamps\n"
    )
    assert post(auth_client, "/data/journal-entries/import", {"content": journal_csv}, expected=200)["created"] == 1
    assert balance_of(auth_client, "Postage") == 25

    bad = (
        "Entry no,Date,Account,Debit,Credit\n"
        f"7,{TODAY},Postage,10,\n"
        f"7,{TODAY},Checking,,9\n"
        f"8,{TODAY},Nowhere,5,\n"
        f"8,{TODAY},Checking,,5\n"
    )
    failed = post(auth_client, "/data/journal-entries/import", {"content": bad}, expected=200)
    assert failed["created"] == 0 and len(failed["errors"]) == 2
    assert balance_of(auth_client, "Postage") == 25  # nothing from the bad file was saved
    assert "Entry no,Date,Account" in auth_client.get(f"{API}/data/journal-entries/export").text
    assert auth_client.get(f"{API}/data/unicorns/export").status_code == 404


def test_notifications(auth_client):
    customer = make_customer(auth_client)
    assert auth_client.get(f"{API}/notifications").json() == []
    post(auth_client, "/invoices", invoice_payload(customer, invoice_date=LAST_WEEK, due_date=YESTERDAY))
    kinds = [note["kind"] for note in auth_client.get(f"{API}/notifications").json()]
    assert kinds == ["overdue_invoices"]


def test_api_keys(auth_client):
    created = post(auth_client, "/company/api-keys", {"name": "Zapier"})
    key = created["key"]
    assert key.startswith("lk_") and created["prefix"] == key[:10]
    assert "key" not in auth_client.get(f"{API}/company/api-keys").json()[0]

    owner_header = auth_client.headers["Authorization"]
    auth_client.headers["Authorization"] = "Bearer " + key
    assert auth_client.get(f"{API}/customers").status_code == 200
    auth_client.headers["Authorization"] = owner_header
    assert auth_client.get(f"{API}/company/api-keys").json()[0]["last_used_at"] is not None

    auth_client.post(f"{API}/company/api-keys/{created['id']}/revoke")
    auth_client.headers["Authorization"] = "Bearer " + key
    assert auth_client.get(f"{API}/customers").status_code == 401
    auth_client.headers["Authorization"] = owner_header


def test_webhooks_are_logged_after_commit(auth_client):
    hook = post(auth_client, "/company/webhooks", {"url": "https://hooks.example.com/digibooks", "events": ["customer.created"]})
    assert len(hook["secret"]) == 48
    make_customer(auth_client, "Hooked Customer")
    post(auth_client, "/invoices", invoice_payload(make_customer(auth_client, "Second")))  # invoice.created is not subscribed
    deliveries = auth_client.get(f"{API}/company/webhook-deliveries").json()
    assert [item["event"] for item in deliveries] == ["customer.created", "customer.created"]
    assert deliveries[0]["status"] == "LOGGED"  # WEBHOOK_DELIVERY=log sends nothing

    # A failed save sends nothing.
    duplicate = auth_client.post(f"{API}/customers", json={"display_name": ""})
    assert duplicate.status_code == 422
    assert len(auth_client.get(f"{API}/company/webhook-deliveries").json()) == 2

    assert auth_client.post(f"{API}/company/webhooks", json={"url": "ftp://x.example.com", "events": ["*"]}).status_code == 422
