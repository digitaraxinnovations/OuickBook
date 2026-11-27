from enum import Enum

from pydantic import BaseModel


class ScoreRating(str, Enum):
    NOT_ENOUGH_HISTORY = "NOT_ENOUGH_HISTORY"
    GOOD = "GOOD"
    WATCH = "WATCH"
    RISKY = "RISKY"


class PaymentScore(BaseModel):
    customer_id: int
    rating: ScoreRating
    paid_invoices: int
    late_invoices: int
    average_days_late: int
    # Unpaid invoices that are long overdue.
    overdue_invoices: int
    reason: str
    suggestion: str
