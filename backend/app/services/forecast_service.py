"""
Cash-flow forecast: the expected bank balance for each coming day.

Starts from today's bank balances and adds what every CashSource expects.
It only reads; nothing is saved or posted.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.core.money import ZERO
from app.forecast.base import CashSource
from app.repositories.journal_repository import JournalRepository
from app.schemas.forecast import DayBalance, ForecastItem, ForecastRead


class ForecastService:
    def __init__(self, settings: Settings, journal_repository: JournalRepository, sources: list[CashSource]):
        self.settings = settings
        self.journal_repository = journal_repository
        self.sources = sources

    def build(self, company_id: int, today: date | None = None) -> ForecastRead:
        today = today or date.today()
        end = today + timedelta(days=self.settings.forecast_days)

        items: list[ForecastItem] = []
        notes: list[str] = []
        for source in self.sources:
            items.extend(source.items(company_id, today, end))
            notes.extend(getattr(source, "notes", []))
        items.sort(key=lambda item: (item.date, item.type, item.description))

        starting = sum((totals.balance for totals in self.journal_repository.bank_totals(company_id, today)), ZERO)
        days = self.daily_balances(starting, items, today, end)
        limit = self.settings.forecast_low_balance
        low_days = [day.date for day in days if day.balance < limit]
        return ForecastRead(
            start_date=today,
            end_date=end,
            starting_balance=starting,
            low_balance_limit=limit,
            days=days,
            items=items,
            lowest=min(days, key=lambda day: day.balance),
            first_low_date=low_days[0] if low_days else None,
            notes=notes,
        )

    @staticmethod
    def daily_balances(starting: Decimal, items: list[ForecastItem], today: date, end: date) -> list[DayBalance]:
        changes: dict[date, Decimal] = {}
        for item in items:
            changes[item.date] = changes.get(item.date, ZERO) + item.amount

        balance = starting
        days = []
        day = today
        while day <= end:
            balance += changes.get(day, ZERO)
            days.append(DayBalance(date=day, balance=balance))
            day += timedelta(days=1)
        return days
