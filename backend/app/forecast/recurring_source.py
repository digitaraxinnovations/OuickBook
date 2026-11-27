"""
Transactions that recurring schedules have not created yet.

Each recurring handler says what its template does to the bank balance
(`cash_effects`), so this class does not need to know the template formats.
Transactions already created are on the books and are counted by the other
sources, so nothing is counted twice.
"""

from datetime import date, timedelta

from app.core.exceptions import AppError
from app.forecast.base import CashSource
from app.recurring.base import RecurringHandler
from app.repositories.contact_repository import CustomerRepository
from app.repositories.recurring_repository import RecurringRepository
from app.services.payment_score_service import PaymentScoreService
from app.services.recurring_service import MAX_RUNS_PER_SCHEDULE, occurrence_date


class RecurringSource(CashSource):
    label = "Recurring"

    def __init__(
        self,
        schedules: RecurringRepository,
        handlers: list[RecurringHandler],
        customers: CustomerRepository,
        scores: PaymentScoreService,
    ):
        self.schedules = schedules
        self.handlers = {handler.transaction_type: handler for handler in handlers}
        self.customers = customers
        self.scores = scores
        self.notes: list[str] = []

    def items(self, company_id, today: date, end: date):
        delays = self.scores.usual_delays(company_id)
        self.notes = []
        result = []
        for schedule in self.schedules.list_all(company_id, active_only=True):
            if schedule.next_date is None:
                continue
            try:
                result.extend(self.items_for(company_id, schedule, delays, today, end))
            except AppError as error:
                self.notes.append(f'Recurring "{schedule.name}" is left out: {error}')
        return result

    def items_for(self, company_id, schedule, delays, today: date, end: date):
        handler = self.handlers[schedule.transaction_type]
        result = []
        for number in range(schedule.run_count, schedule.run_count + MAX_RUNS_PER_SCHEDULE):
            on = occurrence_date(schedule, number)
            if on > end or (schedule.end_date is not None and on > schedule.end_date):
                break
            for effect in handler.cash_effects(company_id, schedule.template, on):
                customer = None
                expected = effect.date
                if effect.customer_id is not None:
                    customer = self.customers.get(company_id, effect.customer_id)
                if effect.on_terms:
                    expected += timedelta(days=delays.get(effect.customer_id, 0))
                expected = max(expected, today)
                if expected <= end:
                    result.append(self.item(expected, effect.amount, schedule.name, customer, "/accounting/recurring"))
        return result
