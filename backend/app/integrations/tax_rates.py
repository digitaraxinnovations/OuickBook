"""
Automatic sales tax rate lookup and e-filing (EXT).

TaxRateProvider is the interface. The app picks one from the
TAX_RATE_PROVIDER setting. Today only "none" exists - rates are entered by hand
on the Sales tax page.

To connect a real provider later (e.g. Avalara or TaxJar):
  1. Write a class that inherits from TaxRateProvider.
     - lookup_rates(): return the rates that apply at an address.
     - file_return(): send a filled-in return for one agency and period.
  2. Return it from build_tax_rate_provider() when TAX_RATE_PROVIDER matches.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError


class FoundRate:
    def __init__(self, name: str, rate: Decimal):
        self.name = name
        self.rate = rate


class TaxRateProvider(ABC):
    provider_name = ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """True when rates can be looked up automatically."""

    @abstractmethod
    def lookup_rates(self, address: str) -> list[FoundRate]:
        """The rates (state, county, city...) that apply at an address."""

    @abstractmethod
    def file_return(self, agency_name: str, period_start: date, period_end: date, amount: Decimal) -> str:
        """File a return electronically; returns the provider's confirmation number."""


class DisabledTaxRateProvider(TaxRateProvider):
    provider_name = "none"

    def is_enabled(self) -> bool:
        return False

    def lookup_rates(self, address: str) -> list[FoundRate]:
        raise BusinessRuleError("Automatic rate lookup is not connected (TAX_RATE_PROVIDER=none). Enter the rate by hand.")

    def file_return(self, agency_name: str, period_start: date, period_end: date, amount: Decimal) -> str:
        raise BusinessRuleError("E-filing is not connected (TAX_RATE_PROVIDER=none). File with the agency, then record the payment here.")


def build_tax_rate_provider(settings: Settings) -> TaxRateProvider:
    if settings.tax_rate_provider == "none":
        return DisabledTaxRateProvider()
    raise BusinessRuleError(f'The tax rate provider "{settings.tax_rate_provider}" is not supported yet. Set TAX_RATE_PROVIDER=none.')
