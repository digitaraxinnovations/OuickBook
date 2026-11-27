"""
Base class for recurring-transaction handlers.

The recurring engine (RecurringService) knows nothing about invoices,
journal entries or bills. Each kind of transaction has a small handler
class that knows how to check a template and create one transaction.

To support a new recurring transaction type:
  1. Add a value to RecurringType (models/enums.py).
  2. Write a handler class that inherits from RecurringHandler
     (check_template, create_transaction and cash_effects).
  3. Add it to build_recurring_handlers() in api/deps.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.enums import RecurringType


@dataclass
class CashEffect:
    """Money one future transaction is expected to move (+ in, - out), in the home currency."""

    date: date
    amount: Decimal
    customer_id: int | None = None
    # True when the customer pays later (an invoice), so their usual delay applies.
    on_terms: bool = False


class RecurringHandler(ABC):
    transaction_type: RecurringType

    @abstractmethod
    def check_template(self, company_id: int, template: dict) -> dict:
        """Validate the template. Return it cleaned up, or raise an AppError."""

    @abstractmethod
    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        """Create one transaction from the template and return its id."""

    @abstractmethod
    def cash_effects(self, company_id: int, template: dict, transaction_date: date) -> list[CashEffect]:
        """What the transaction created on this date will do to the bank balance (used by the forecast)."""
