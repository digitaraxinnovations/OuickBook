"""
Test setup.

Tests run against a separate PostgreSQL database (TEST_POSTGRES_DB in .env).
Every test starts with empty tables, so tests never affect each other
or your real data.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers every table)
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

test_engine = create_engine(settings.get_test_database_url())
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def get_test_db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


def reset_test_database():
    """Throw away every table in the TEST database and create them fresh."""
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(test_engine)


@pytest.fixture
def client():
    reset_test_database()
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    """A client that is already signed in as a new company owner."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Test Owner",
            "company_name": "Test Company",
            "email": "owner@example.com",
            "password": "secret-password",
        },
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
