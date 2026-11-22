"""
Automatic bank feeds (EXT).

BankFeedProvider is the interface. The app picks one from the
BANK_FEED_PROVIDER setting:
- "none": transactions come in by uploading CSV / OFX / QFX statement files.
- "mock": a simulated feed that produces sample bank lines (same lines every
  time, so a repeat sync reports duplicates and a later day adds new ones).

To connect a real provider later (e.g. Plaid):
  1. Write a class that inherits from BankFeedProvider.
     - connect_url(): start the provider's "link your bank" screen.
     - fetch_transactions(): return new StatementLine objects since a date.
  2. Return it from build_bank_feed_provider() when BANK_FEED_PROVIDER matches.
BankImportService already de-duplicates and applies bank rules to whatever comes in.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal

from app.banking.statement_parsers import StatementLine
from app.core.config import Settings
from app.core.exceptions import BusinessRuleError
from app.core.money import to_money


class BankFeedProvider(ABC):
    provider_name = ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """True when accounts can be connected to a live feed."""

    @abstractmethod
    def fetch_transactions(self, company_id: int, account_id: int, since: date | None) -> list[StatementLine]:
        """Download new transactions for one connected account."""


class DisabledBankFeedProvider(BankFeedProvider):
    provider_name = "none"

    def is_enabled(self) -> bool:
        return False

    def fetch_transactions(self, company_id: int, account_id: int, since: date | None) -> list[StatementLine]:
        raise BusinessRuleError(
            "Bank feeds are not connected yet (BANK_FEED_PROVIDER=none). Upload a CSV, OFX or QFX statement instead."
        )


# (description, base amount) - negative = money out. Two are picked for every day.
SAMPLE_LINES = [
    ("SHELL OIL 4421 SPRINGFIELD", Decimal("-48.30")),
    ("CITY POWER & LIGHT AUTOPAY", Decimal("-145.20")),
    ("MOBILE DEPOSIT", Decimal("320.00")),
    ("OFFICE DEPOT #2217", Decimal("-62.75")),
    ("MONTHLY SERVICE FEE", Decimal("-12.00")),
    ("CUSTOMER PAYMENT ACH", Decimal("450.00")),
    ("GREEN SUPPLY CO", Decimal("-210.40")),
    ("HARDWARE WORLD #118", Decimal("-37.99")),
]
LINES_PER_DAY = 2


class MockBankFeedProvider(BankFeedProvider):
    """A simulated bank: the same sample lines for the same day and account, every time."""

    provider_name = "mock"

    def __init__(self, days: int):
        self.days = days

    def is_enabled(self) -> bool:
        return True

    def fetch_transactions(self, company_id: int, account_id: int, since: date | None) -> list[StatementLine]:
        today = date.today()
        first = today - timedelta(days=self.days - 1)
        if since is not None and since > first:
            first = since
        lines = []
        day = first
        while day <= today:
            for n in range(LINES_PER_DAY):
                description, base = SAMPLE_LINES[(day.toordinal() + n * 3) % len(SAMPLE_LINES)]
                size = abs(base) + Decimal(day.toordinal() % 9)  # the amounts vary a little from day to day
                amount = to_money(size if base > 0 else -size)
                lines.append(StatementLine(day, description, amount, f"mock-{account_id}-{day.isoformat()}-{n}"))
            day += timedelta(days=1)
        return lines


def build_bank_feed_provider(settings: Settings) -> BankFeedProvider:
    if settings.bank_feed_provider == "none":
        return DisabledBankFeedProvider()
    if settings.bank_feed_provider == "mock":
        return MockBankFeedProvider(settings.mock_bank_feed_days)
    raise BusinessRuleError(f'The bank feed provider "{settings.bank_feed_provider}" is not supported yet. Set BANK_FEED_PROVIDER=none or mock.')
