API = "/api/v1"


def test_signup_creates_company_with_chart_of_accounts(auth_client):
    me = auth_client.get(f"{API}/auth/me").json()
    assert me["company"]["name"] == "Test Company"

    accounts = auth_client.get(f"{API}/accounts").json()
    names = [account["name"] for account in accounts]
    assert "Checking" in names
    assert "Accounts Receivable (A/R)" in names


def test_login_with_wrong_password_fails(auth_client):
    response = auth_client.post(f"{API}/auth/login", json={"email": "owner@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_duplicate_email_is_rejected(auth_client):
    response = auth_client.post(
        f"{API}/auth/signup",
        json={"full_name": "Someone", "company_name": "Other", "email": "owner@example.com", "password": "secret-password"},
    )
    assert response.status_code == 409


def test_requests_without_token_are_rejected(client):
    response = client.get(f"{API}/customers")
    assert response.status_code == 401
