import datetime
from decimal import Decimal

from pydantic import BaseModel


class ForecastItem(BaseModel):
    """One expected movement of money."""

    date: datetime.date
    amount: Decimal  # + money in, - money out
    type: str
    description: str
    # Set on money from a customer, so "what if they pay late?" can move it.
    customer_id: int | None = None
    customer_name: str | None = None
    # Page of the record behind this item.
    link: str | None = None


class DayBalance(BaseModel):
    date: datetime.date
    balance: Decimal


class ForecastRead(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    starting_balance: Decimal
    # A balance under this is a warning.
    low_balance_limit: Decimal
    days: list[DayBalance]
    items: list[ForecastItem]
    lowest: DayBalance
    first_low_date: datetime.date | None
    # Things that could not be included, and why.
    notes: list[str]
