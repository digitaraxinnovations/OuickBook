"""
Automatic sales tax rate lookup and e-filing (EXT).

TaxRateProvider is the interface. The app picks one from the
TAX_RATE_PROVIDER setting:
- "none": rates are entered by hand on the Sales tax page.
- "mock": rates are "looked up" from the state and ZIP in an address, and a
  return can be "e-filed" (it gets a made-up confirmation number).

To connect a real provider later (e.g. Avalara or TaxJar):
  1. Write a class that inherits from TaxRateProvider.
     - lookup_rates(): return the rates that apply at an address.
     - file_return(): send a filled-in return for one agency and period.
  2. Return it from build_tax_rate_provider() when TAX_RATE_PROVIDER matches.
"""

import hashlib
import re
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


# State sales tax in percent (sample data for the mock provider).
SAMPLE_STATE_RATES = {
    "IL": ("Illinois state tax", Decimal("6.25")),
    "CA": ("California state tax", Decimal("7.25")),
    "TX": ("Texas state tax", Decimal("6.25")),
    "NY": ("New York state tax", Decimal("4.00")),
    "FL": ("Florida state tax", Decimal("6.00")),
    "WA": ("Washington state tax", Decimal("6.50")),
    "OH": ("Ohio state tax", Decimal("5.75")),
    "PA": ("Pennsylvania state tax", Decimal("6.00")),
    "GA": ("Georgia state tax", Decimal("4.00")),
    "MI": ("Michigan state tax", Decimal("6.00")),
    "NC": ("North Carolina state tax", Decimal("4.75")),
    "AZ": ("Arizona state tax", Decimal("5.60")),
}
STATE_AND_ZIP = re.compile(r"\b([A-Za-z]{2})\s+(\d{5})\b")


class MockTaxRateProvider(TaxRateProvider):
    """Simulated rate lookup and e-filing."""

    provider_name = "mock"

    def __init__(self, default_rate: Decimal):
        self.default_rate = default_rate

    def is_enabled(self) -> bool:
        return True

    def lookup_rates(self, address: str) -> list[FoundRate]:
        match = STATE_AND_ZIP.search(address or "")
        if match is None or match.group(1).upper() not in SAMPLE_STATE_RATES:
            return [FoundRate("Sales tax (default rate)", self.default_rate)]
        name, state_rate = SAMPLE_STATE_RATES[match.group(1).upper()]
        zip_code = match.group(2)
        local_rate = Decimal("0.25") * (1 + int(zip_code) % 6)  # 0.25% - 1.50%, the same for the same ZIP
        return [FoundRate(name, state_rate), FoundRate(f"Local tax {zip_code}", local_rate)]

    def file_return(self, agency_name: str, period_start: date, period_end: date, amount: Decimal) -> str:
        fingerprint = hashlib.sha1(f"{agency_name}|{period_start}|{period_end}|{amount}".encode()).hexdigest()[:6].upper()
        return f"MOCK-EF-{period_end:%Y%m%d}-{fingerprint}"


def build_tax_rate_provider(settings: Settings) -> TaxRateProvider:
    if settings.tax_rate_provider == "none":
        return DisabledTaxRateProvider()
    if settings.tax_rate_provider == "mock":
        return MockTaxRateProvider(settings.mock_tax_default_rate)
    raise BusinessRuleError(f'The tax rate provider "{settings.tax_rate_provider}" is not supported yet. Set TAX_RATE_PROVIDER=none or mock.')
