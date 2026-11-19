"""
Small date helpers.
"""

import calendar
from datetime import date, timedelta


def add_months(start: date, months: int) -> date:
    """Add months to a date. Jan 31 + 1 month = Feb 28 (or 29), never an error."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def add_days(start: date, days: int) -> date:
    return start + timedelta(days=days)
