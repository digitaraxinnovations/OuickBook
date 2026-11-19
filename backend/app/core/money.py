"""
Small helpers for money values.

All money is stored as Decimal with 2 decimal places. Never use float for money.
"""

from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def to_money(value) -> Decimal:
    """Convert a number (int, str, float or Decimal) to a 2-decimal Decimal."""
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
