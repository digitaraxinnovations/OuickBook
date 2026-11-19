from datetime import date

from sqlalchemy import JSON, Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.enums import RecurringFrequency, RecurringType


class RecurringSchedule(CompanyOwnedMixin, TimestampMixin, Base):
    """
    A saved transaction that is created again on a schedule
    (e.g. a monthly depreciation journal entry).

    `template` holds the transaction details as JSON, in the same shape the
    matching "create" API expects, minus the date.
    """

    __tablename__ = "recurring_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    transaction_type: Mapped[RecurringType] = mapped_column(Enum(RecurringType, native_enum=False, length=30))
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency, native_enum=False, length=20))
    # "Every 2 months" -> frequency MONTHLY, interval 2
    interval: Mapped[int] = mapped_column(default=1)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_date: Mapped[date | None] = mapped_column(Date, index=True)
    # How many transactions have been created so far
    run_count: Mapped[int] = mapped_column(default=0)
    last_run_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)
    template: Mapped[dict] = mapped_column(JSON)
