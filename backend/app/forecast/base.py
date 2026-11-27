"""
Base classes for the cash-flow forecast.

Each kind of expected money (open invoices, bills, payroll...) is one
CashSource. ForecastService adds them up and knows nothing about the details.

To forecast something new:
  1. Write a class that inherits from CashSource.
  2. Add it to build_forecast_service() in api/deps.py.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.schemas.forecast import ForecastItem


class CashSource(ABC):
    # Shown in the "Type" column, e.g. "Invoice" or "Payroll".
    label: str = ""

    @abstractmethod
    def items(self, company_id: int, today: date, end: date) -> list[ForecastItem]:
        """Money expected between today and `end`, in the home currency (+ in, - out)."""

    def item(self, on: date, amount: Decimal, description: str, customer=None, link: str | None = None) -> ForecastItem:
        return ForecastItem(
            date=on,
            amount=amount,
            type=self.label,
            description=description,
            customer_id=customer.id if customer else None,
            customer_name=customer.display_name if customer else None,
            link=link,
        )
