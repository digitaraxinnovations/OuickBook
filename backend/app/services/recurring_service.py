"""
Recurring transactions: saving schedules and creating the transactions when they are due.
"""

from datetime import date

from app.core.dates import add_days, add_months
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import RecurringSchedule
from app.models.enums import RecurringFrequency, RecurringType
from app.recurring.base import RecurringHandler
from app.repositories.recurring_repository import RecurringRepository
from app.schemas.recurring import CreatedTransaction, RecurringScheduleWrite
from app.services.base import BaseService

# Safety limit so a schedule far in the past cannot create thousands of transactions at once.
MAX_RUNS_PER_SCHEDULE = 400


def occurrence_date(schedule: RecurringSchedule, number: int) -> date:
    """
    Date of the Nth transaction (0 = the first one, on the start date).
    Always counted from the start date, so "the 31st of every month"
    does not drift to the 28th after February.
    """
    steps = number * schedule.interval
    if schedule.frequency == RecurringFrequency.DAILY:
        return add_days(schedule.start_date, steps)
    if schedule.frequency == RecurringFrequency.WEEKLY:
        return add_days(schedule.start_date, steps * 7)
    if schedule.frequency == RecurringFrequency.MONTHLY:
        return add_months(schedule.start_date, steps)
    return add_months(schedule.start_date, steps * 12)


class RecurringService(BaseService):
    def __init__(self, session, repository: RecurringRepository, handlers: list[RecurringHandler]):
        super().__init__(session)
        self.repository = repository
        self.handlers = {}
        for handler in handlers:
            self.handlers[handler.transaction_type] = handler

    # ---------- reading ----------

    def list(self, company_id: int) -> list[RecurringSchedule]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, schedule_id: int) -> RecurringSchedule:
        schedule = self.repository.get(company_id, schedule_id)
        if schedule is None:
            raise NotFoundError("Recurring schedule not found.")
        return schedule

    # ---------- writing ----------

    def create(self, company_id: int, data: RecurringScheduleWrite) -> RecurringSchedule:
        schedule = RecurringSchedule(company_id=company_id, run_count=0)
        self.apply_changes(company_id, schedule, data)
        self.repository.add(schedule)
        self.commit()
        return schedule

    def update(self, company_id: int, schedule_id: int, data: RecurringScheduleWrite) -> RecurringSchedule:
        schedule = self.get(company_id, schedule_id)
        if data.transaction_type != schedule.transaction_type:
            raise BusinessRuleError("The transaction type of a schedule cannot be changed.")
        if data.start_date != schedule.start_date and schedule.run_count > 0:
            raise BusinessRuleError("The start date cannot change after the schedule has run.")
        self.apply_changes(company_id, schedule, data)
        self.commit()
        return schedule

    def apply_changes(self, company_id: int, schedule: RecurringSchedule, data: RecurringScheduleWrite) -> None:
        if data.end_date is not None and data.end_date < data.start_date:
            raise BusinessRuleError("The end date cannot be before the start date.")

        handler = self.get_handler(data.transaction_type)
        schedule.template = handler.check_template(company_id, data.template)
        schedule.name = data.name
        schedule.transaction_type = data.transaction_type
        schedule.frequency = data.frequency
        schedule.interval = data.interval
        schedule.start_date = data.start_date
        schedule.end_date = data.end_date
        schedule.is_active = data.is_active
        self.refresh_next_date(schedule)

    # ---------- running ----------

    def run_due(self, company_id: int, today: date) -> list[CreatedTransaction]:
        """Create every transaction that is due on or before `today`."""
        created = []
        for schedule in self.repository.list_due(company_id, today):
            handler = self.get_handler(schedule.transaction_type)
            runs = 0
            while schedule.next_date is not None and schedule.next_date <= today and runs < MAX_RUNS_PER_SCHEDULE:
                transaction_date = schedule.next_date
                # The handler's service commits the transaction.
                transaction_id = handler.create_transaction(company_id, schedule.template, transaction_date)
                schedule.run_count += 1
                schedule.last_run_date = transaction_date
                self.refresh_next_date(schedule)
                self.commit()
                runs += 1
                created.append(
                    CreatedTransaction(
                        schedule_id=schedule.id,
                        schedule_name=schedule.name,
                        transaction_type=schedule.transaction_type,
                        transaction_id=transaction_id,
                        transaction_date=transaction_date,
                    )
                )
        return created

    def refresh_next_date(self, schedule: RecurringSchedule) -> None:
        next_date = occurrence_date(schedule, schedule.run_count)
        if schedule.end_date is not None and next_date > schedule.end_date:
            schedule.next_date = None  # finished
        else:
            schedule.next_date = next_date

    def get_handler(self, transaction_type: RecurringType) -> RecurringHandler:
        handler = self.handlers.get(transaction_type)
        if handler is None:
            raise BusinessRuleError(f"Recurring {transaction_type.value} is not supported yet.")
        return handler
