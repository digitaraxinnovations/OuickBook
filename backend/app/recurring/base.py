"""
Base class for recurring-transaction handlers.

The recurring engine (RecurringService) knows nothing about invoices,
journal entries or bills. Each kind of transaction has a small handler
class that knows how to check a template and create one transaction.

To support a new recurring transaction type:
  1. Add a value to RecurringType (models/enums.py).
  2. Write a handler class that inherits from RecurringHandler.
  3. Add it to build_recurring_handlers() in api/deps.py.
"""

from abc import ABC, abstractmethod
from datetime import date

from app.models.enums import RecurringType


class RecurringHandler(ABC):
    transaction_type: RecurringType

    @abstractmethod
    def check_template(self, company_id: int, template: dict) -> dict:
        """Validate the template. Return it cleaned up, or raise an AppError."""

    @abstractmethod
    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        """Create one transaction from the template and return its id."""
