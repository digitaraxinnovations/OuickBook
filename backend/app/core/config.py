"""
Central configuration for the backend.

Every setting is read from environment variables or from the project's
root .env file. The rest of the code must NOT read os.environ directly -
it should import `settings` from this module instead.
"""

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
    app_name: str = "Ledgerly"
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
    # "none" = the "Pay now" button is hidden. A real provider (e.g. Stripe)
    # can be added later as a new PaymentProcessor class - see app/integrations/payments.
    payment_provider: str = "none"
    payment_provider_secret_key: str = ""

    # ---------- Bank feeds (EXT) ----------
    # "none" = no live feed; import CSV / OFX / QFX statements instead.
    # A provider such as Plaid can be added in app/integrations/bank_feeds.py.
    bank_feed_provider: str = "none"
    bank_feed_client_id: str = ""
    bank_feed_secret: str = ""
    # How many days apart a bank line and a book transaction can be and still be suggested as a match.
    bank_match_days: int = 14

    # ---------- Sales tax rates / e-filing (EXT) ----------
    # "none" = rates are entered by hand on the Sales tax page.
    # A provider such as Avalara can be added in app/integrations/tax_rates.py.
    tax_rate_provider: str = "none"
    tax_rate_api_key: str = ""

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
