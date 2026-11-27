"""Customer payment score: Good / Watch / Risky from how late invoices were paid."""

from datetime import date, timedelta

from tests.test_phase2_sales import API, make_customer, make_invoice

TODAY = date.today()


def day(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).isoformat()


def invoice_paid_late(client, customer_id, days_late: int, due_days_ago: int = 100):
    """An invoice due `due_days_ago`, paid in full `days_late` days after that (negative = early)."""
    invoice = make_invoice(client, customer_id, invoice_date=day(due_days_ago + 10), due_date=day(due_days_ago))
    payment = {
        "customer_id": customer_id,
        "payment_date": day(due_days_ago - days_late),
        "amount": "100",
        "applications": [{"invoice_id": invoice["id"], "amount": "100"}],
    }
    response = client.post(f"{API}/payments", json=payment)
    assert response.status_code == 201, response.text


def score_of(client, customer_id):
    response = client.get(f"{API}/customers/{customer_id}/payment-score")
    assert response.status_code == 200, response.text
    return response.json()


def customer_who_pays(client, name, *days_late):
    customer = make_customer(client, name)
    for days in days_late:
        invoice_paid_late(client, customer, days)
    return customer


def test_ratings_follow_the_average_days_late(auth_client):
    good = customer_who_pays(auth_client, "On Time", -5, 0, 9)  # average 3
    watch = customer_who_pays(auth_client, "Slow", 0, 20, 70)  # average 30
    risky = customer_who_pays(auth_client, "Very Slow", 31, 31, 31)
    new = customer_who_pays(auth_client, "New", 40, 40)

    assert score_of(auth_client, good)["rating"] == "GOOD"
    assert score_of(auth_client, watch)["rating"] == "WATCH"
    assert score_of(auth_client, risky)["rating"] == "RISKY"
    assert score_of(auth_client, new)["rating"] == "NOT_ENOUGH_HISTORY"

    slow = score_of(auth_client, watch)
    assert (slow["paid_invoices"], slow["late_invoices"], slow["average_days_late"]) == (3, 2, 30)
    assert slow["reason"] == "Paid 2 of 3 invoice(s) late, 30 day(s) late on average."

    listed = {row["customer_id"]: row["rating"] for row in auth_client.get(f"{API}/customers/payment-scores").json()}
    assert listed == {good: "GOOD", watch: "WATCH", risky: "RISKY", new: "NOT_ENOUGH_HISTORY"}


def test_a_long_overdue_invoice_is_a_warning(auth_client):
    good = customer_who_pays(auth_client, "Usually Fine", 0, 0, 0)
    make_invoice(auth_client, good, invoice_date=day(41), due_date=day(31))
    result = score_of(auth_client, good)
    assert result["rating"] == "WATCH" and result["overdue_invoices"] == 1

    new = make_customer(auth_client, "Never Paid")
    make_invoice(auth_client, new, invoice_date=day(40), due_date=day(30))  # exactly 30 days: not yet
    assert score_of(auth_client, new)["rating"] == "NOT_ENOUGH_HISTORY"


def test_other_companies_cannot_see_a_score(auth_client):
    customer = customer_who_pays(auth_client, "Private", 50, 50, 50)
    other = auth_client.post(
        f"{API}/auth/signup",
        json={"full_name": "Other", "company_name": "Other Co", "email": "other@example.com", "password": "secret-password"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {other}"}
    assert auth_client.get(f"{API}/customers/{customer}/payment-score", headers=headers).status_code == 404
    assert auth_client.get(f"{API}/customers/payment-scores", headers=headers).json() == []
