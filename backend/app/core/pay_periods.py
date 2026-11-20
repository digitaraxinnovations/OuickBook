"""
Pay period dates for each pay frequency.

- Weekly / every two weeks: periods of 7 / 14 days.
- Twice a month: the 1st-15th and the 16th-end of the month.
- Monthly: a calendar month (or the same day each month).

Frequencies are the PayFrequency values ("WEEKLY", "BIWEEKLY", "SEMIMONTHLY",
"MONTHLY"); plain text is used here so this module does not depend on the models.
"""

from datetime import date, timedelta

from app.core.dates import add_months

PERIODS_PER_YEAR = {
    "WEEKLY": 52,
    "BIWEEKLY": 26,
    "SEMIMONTHLY": 24,
    "MONTHLY": 12,
}

DAYS_PER_PERIOD = {"WEEKLY": 7, "BIWEEKLY": 14}


def last_day_of_month(day: date) -> date:
    first_of_next = add_months(day.replace(day=1), 1)
    return first_of_next - timedelta(days=1)


def is_month_end(day: date) -> bool:
    return day == last_day_of_month(day)


def previous_period_end(frequency: str, period_end: date) -> date:
    if frequency in DAYS_PER_PERIOD:
        return period_end - timedelta(days=DAYS_PER_PERIOD[frequency])
    if frequency == "SEMIMONTHLY":
        if period_end.day <= 15:
            return period_end.replace(day=1) - timedelta(days=1)
        return period_end.replace(day=15)
    # Monthly
    if is_month_end(period_end):
        return period_end.replace(day=1) - timedelta(days=1)
    return add_months(period_end, -1)


def next_period_end(frequency: str, period_end: date) -> date:
    if frequency in DAYS_PER_PERIOD:
        return period_end + timedelta(days=DAYS_PER_PERIOD[frequency])
    if frequency == "SEMIMONTHLY":
        if period_end.day <= 15:
            return last_day_of_month(period_end)
        return add_months(period_end.replace(day=15), 1)
    # Monthly
    if is_month_end(period_end):
        return last_day_of_month(add_months(period_end.replace(day=1), 1))
    return add_months(period_end, 1)


def period_start(frequency: str, period_end: date) -> date:
    return previous_period_end(frequency, period_end) + timedelta(days=1)
