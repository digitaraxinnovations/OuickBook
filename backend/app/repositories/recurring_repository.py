from datetime import date

from sqlalchemy import select

from app.models import RecurringSchedule
from app.repositories.base import BaseRepository


class RecurringRepository(BaseRepository):
    model = RecurringSchedule

    def order_by_columns(self) -> list:
        return [RecurringSchedule.name]

    def list_due(self, company_id: int, today: date) -> list[RecurringSchedule]:
        query = (
            select(RecurringSchedule)
            .where(
                RecurringSchedule.company_id == company_id,
                RecurringSchedule.is_active.is_(True),
                RecurringSchedule.next_date.is_not(None),
                RecurringSchedule.next_date <= today,
            )
            .order_by(RecurringSchedule.next_date, RecurringSchedule.id)
        )
        return list(self.session.scalars(query))

    def company_ids_with_due_schedules(self, today: date) -> list[int]:
        """Used by the scheduled job that runs for every company."""
        query = (
            select(RecurringSchedule.company_id)
            .where(
                RecurringSchedule.is_active.is_(True),
                RecurringSchedule.next_date.is_not(None),
                RecurringSchedule.next_date <= today,
            )
            .distinct()
        )
        return list(self.session.scalars(query))
