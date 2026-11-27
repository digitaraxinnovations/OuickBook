"""
Central configuration for the backend.

Every setting is read from environment variables or from the project's
root .env file. The rest of the code must NOT read os.environ directly -
it should import `settings` from this module instead.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py  ->  parents[3] is the project root folder
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Application ----------
    app_name: str = "DigiBooks"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # ---------- Database ----------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "ledgerly"
    postgres_password: str = ""
    postgres_db: str = "ledgerly"
    # Python database driver: "psycopg" (fast, uses a compiled library) or
    # "pg8000" (pure Python - use it if Windows Application Control blocks psycopg).
    postgres_driver: str = "psycopg"
    database_echo: bool = False
    # Optional full URL. When set, it wins over the POSTGRES_* values.
    database_url: str | None = None
    # Separate database used only by the automated tests (it is wiped on every run).
    test_postgres_db: str = "ledgerly_test"

    # ---------- Security ----------
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    bcrypt_rounds: int = 12

    # ---------- CORS ----------
    cors_origins: list[str] = ["http://localhost:3000"]

    # ---------- Business defaults ----------
    default_currency: str = "USD"
    default_payment_terms_days: int = 30
    # First number for invoices, estimates, sales receipts, credit memos...
    invoice_number_start: int = 1001
    # Largest company logo that can be uploaded, in bytes.
    max_logo_bytes: int = 500_000
    # Largest receipt / attachment file, in bytes.
    max_attachment_bytes: int = 5_000_000
    # Vendors paid at least this much in a year get a 1099 form.
    form_1099_threshold: int = 600
    # First check number when a bank account has never printed a check.
    first_check_number: int = 1001

    # ---------- Links sent to customers ----------
    # The frontend address customers open (invoice "view and pay" links).
    public_app_url: str = "http://localhost:3000"

    # ---------- Email (EXT) ----------
    # "log"  = do not send; just record the email in the app's email log (default, no setup needed)
    # "smtp" = send through the SMTP server below
    email_provider: str = "log"
    email_from: str = "no-reply@example.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # ---------- Online card/bank payments on invoices (EXT) ----------
    # "none" = the "Pay now" button is hidden. "mock" = a simulated checkout page (no real money).
    # A real provider (e.g. Stripe) can be added later as a new PaymentProcessor class - see app/integrations/payments.
    payment_provider: str = "none"
    payment_provider_secret_key: str = ""

    # ---------- Bank feeds (EXT) ----------
    # "none" = no live feed; import CSV / OFX / QFX statements instead.
    # "mock" = a simulated feed that produces sample bank lines.
    # A provider such as Plaid can be added in app/integrations/bank_feeds.py.
    bank_feed_provider: str = "none"
    bank_feed_client_id: str = ""
    bank_feed_secret: str = ""
    # How many days apart a bank line and a book transaction can be and still be suggested as a match.
    bank_match_days: int = 14

    # ---------- Sales tax rates / e-filing (EXT) ----------
    # "none" = rates are entered by hand on the Sales tax page.
    # "mock" = simulated rate lookup by address and simulated e-filing.
    # A provider such as Avalara can be added in app/integrations/tax_rates.py.
    tax_rate_provider: str = "none"
    tax_rate_api_key: str = ""

    # ---------- Payroll ----------
    # Overtime pay = hourly rate x this.
    payroll_overtime_multiplier: Decimal = Decimal("1.5")
    # (EXT) "none" = taxes are pay items you set up; direct deposit is sent by you.
    # "mock" = simulated payroll taxes and simulated direct deposit.
    # A payroll service can be added in app/integrations/payroll.py.
    payroll_provider: str = "none"
    payroll_provider_api_key: str = ""

    # ---------- Built-in mock providers (simulated; no real money moves) ----------
    # Used when a provider setting above is "mock".
    mock_bank_feed_days: int = 14  # how many days of sample bank lines the first sync brings in
    mock_tax_default_rate: Decimal = Decimal("6.00")  # sales tax % when the address has no known state
    mock_federal_income_tax_percent: Decimal = Decimal("10")
    mock_social_security_percent: Decimal = Decimal("6.2")  # employee and employer each
    mock_medicare_percent: Decimal = Decimal("1.45")  # employee and employer each

    # ---------- Customer payment score ----------
    # Average days late: up to GOOD is "Good", up to WATCH is "Watch", more is "Risky".
    score_good_max_days: int = 3
    score_watch_max_days: int = 30
    score_min_invoices: int = 3  # fewer paid invoices = "Not enough history"
    score_overdue_days: int = 30  # an unpaid invoice later than this counts against the customer

    # ---------- Cash-flow forecast ----------
    forecast_days: int = 90
    forecast_low_balance: Decimal = Decimal("0")  # warn when the balance goes under this
    forecast_tax_due_days: int = 20  # sales tax is paid this many days after its period ends

    # ---------- Books health check ----------
    health_lookback_days: int = 365  # how far back spending is checked
    health_duplicate_days: int = 7  # same vendor and amount this close = possible duplicate
    health_unusual_factor: Decimal = Decimal("3")  # times the vendor's typical amount
    health_unusual_min_history: int = 3
    health_receipt_min: Decimal = Decimal("75")  # larger expenses need a receipt
    health_reconcile_days: int = 45
    health_overdue_days: int = 90
    health_undeposited_days: int = 14
    health_points_high: int = 10
    health_points_medium: int = 5
    health_points_low: int = 2
    health_max_points_per_check: int = 25

    # ---------- Exchange rates (EXT) ----------
    # "none" = rates are typed in on Settings -> Currencies.
    # A rates service can be added in app/integrations/exchange_rates.py.
    exchange_rate_provider: str = "none"
    exchange_rate_api_key: str = ""

    # ---------- Webhooks (EXT) ----------
    # "log" = record what would be sent, send nothing. "http" = really POST to each webhook URL.
    webhook_delivery: str = "log"
    webhook_timeout_seconds: int = 5

    def get_database_url(self) -> str:
        """Return the SQLAlchemy connection URL for PostgreSQL."""
        if self.database_url:
            return self.database_url
        return self.build_postgres_url(self.postgres_db)

    def get_test_database_url(self) -> str:
        return self.build_postgres_url(self.test_postgres_db)

    def build_postgres_url(self, database_name: str) -> str:
        return (
            f"postgresql+{self.postgres_driver}://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse the same object everywhere."""
    return Settings()


settings = get_settings()
