"""
Automatic bank feeds (EXT).

BankFeedProvider is the interface. The app picks one from the
BANK_FEED_PROVIDER setting. Today only "none" exists - transactions come in
by uploading CSV / OFX / QFX statement files instead.

To connect a real provider later (e.g. Plaid):
  1. Write a class that inherits from BankFeedProvider.
     - connect_url(): start the provider's "link your bank" screen.
     - fetch_transactions(): return new StatementLine objects since a date.
  2. Return it from build_bank_feed_provider() when BANK_FEED_PROVIDER matches.
BankImportService already de-duplicates and applies bank rules to whatever comes in.
"""

from abc import ABC, abstractmethod
from datetime import date

from app.banking.statement_parsers import StatementLine
from app.core.config import Settings
from app.core.exceptions import BusinessRuleError


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


def build_bank_feed_provider(settings: Settings) -> BankFeedProvider:
    if settings.bank_feed_provider == "none":
        return DisabledBankFeedProvider()
    raise BusinessRuleError(f'The bank feed provider "{settings.bank_feed_provider}" is not supported yet. Set BANK_FEED_PROVIDER=none.')
