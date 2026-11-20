"""
Payroll tax calculation, tax filing and direct deposit (EXT).

PayrollProvider is the interface. The app picks one from the
PAYROLL_PROVIDER setting. Today only "none" exists:
- no taxes are worked out automatically - add tax pay items (e.g. "Federal
  income tax" as a percent) and edit the amounts on each paycheck;
- direct deposit paychecks are recorded, but the money must be sent from
  your bank yourself;
- tax forms are filed by you; record the payment under Payroll liabilities.

To connect a real payroll service later:
  1. Write a class that inherits from PayrollProvider.
  2. Return it from build_payroll_provider() when PAYROLL_PROVIDER matches.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError


class CalculatedTax:
    """A tax the provider worked out for one paycheck."""

    def __init__(self, name: str, amount: Decimal, paid_by_employer: bool):
        self.name = name
        self.amount = amount
        self.paid_by_employer = paid_by_employer


class PayrollProvider(ABC):
    provider_name = ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """True when taxes are calculated and money is sent by the provider."""

    @abstractmethod
    def calculate_taxes(self, employee_id: int, gross_pay: Decimal, pay_date: date) -> list[CalculatedTax]:
        """Employee and employer taxes for one paycheck."""

    @abstractmethod
    def send_direct_deposit(self, employee_id: int, amount: Decimal, pay_date: date) -> str:
        """Send net pay to the employee's bank; returns a reference."""


class DisabledPayrollProvider(PayrollProvider):
    provider_name = "none"

    def is_enabled(self) -> bool:
        return False

    def calculate_taxes(self, employee_id: int, gross_pay: Decimal, pay_date: date) -> list[CalculatedTax]:
        return []

    def send_direct_deposit(self, employee_id: int, amount: Decimal, pay_date: date) -> str:
        raise BusinessRuleError("Direct deposit is not connected (PAYROLL_PROVIDER=none). Send the money from your bank.")


def build_payroll_provider(settings: Settings) -> PayrollProvider:
    if settings.payroll_provider == "none":
        return DisabledPayrollProvider()
    raise BusinessRuleError(f'The payroll provider "{settings.payroll_provider}" is not supported yet. Set PAYROLL_PROVIDER=none.')
