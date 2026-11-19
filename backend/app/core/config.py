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
    invoice_number_start: int = 1001

    def get_database_url(self) -> str:
        """Return the SQLAlchemy connection URL for PostgreSQL."""
        if self.database_url:
            return self.database_url
        return self.build_postgres_url(self.postgres_db)

    def get_test_database_url(self) -> str:
        return self.build_postgres_url(self.test_postgres_db)

    def build_postgres_url(self, database_name: str) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse the same object everywhere."""
    return Settings()


settings = get_settings()
