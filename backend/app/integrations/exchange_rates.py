"""
Live exchange rates (EXT).

ExchangeRateProvider is the interface. The app picks one from the
EXCHANGE_RATE_PROVIDER setting. Today only "none" exists - rates are typed in
on Settings -> Currencies.

To connect a rates service later:
  1. Write a class that inherits from ExchangeRateProvider (rate_for()).
  2. Return it from build_exchange_rate_provider() when EXCHANGE_RATE_PROVIDER matches.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError


class ExchangeRateProvider(ABC):
    provider_name = ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """True when rates can be downloaded."""

    @abstractmethod
    def rate_for(self, home_currency: str, foreign_currency: str, on_date: date) -> Decimal:
        """Home currency for 1 unit of the foreign currency on a date."""


class DisabledExchangeRateProvider(ExchangeRateProvider):
    provider_name = "none"

    def is_enabled(self) -> bool:
        return False

    def rate_for(self, home_currency: str, foreign_currency: str, on_date: date) -> Decimal:
        raise BusinessRuleError("Live exchange rates are not connected (EXCHANGE_RATE_PROVIDER=none). Enter the rate by hand.")


def build_exchange_rate_provider(settings: Settings) -> ExchangeRateProvider:
    if settings.exchange_rate_provider == "none":
        return DisabledExchangeRateProvider()
    raise BusinessRuleError(f'The exchange rate provider "{settings.exchange_rate_provider}" is not supported yet. Set EXCHANGE_RATE_PROVIDER=none.')
