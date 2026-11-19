from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import RecurringFrequency, RecurringType
from app.schemas.common import CleanStringsModel, ORMModel


class RecurringScheduleWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    transaction_type: RecurringType
    frequency: RecurringFrequency
    interval: int = Field(default=1, ge=1, le=99)
    start_date: date
    end_date: date | None = None
    is_active: bool = True
    # Same fields as the matching create request, without the date.
    template: dict


class RecurringScheduleRead(ORMModel):
    id: int
    name: str
    transaction_type: RecurringType
    frequency: RecurringFrequency
    interval: int
    start_date: date
    end_date: date | None
    next_date: date | None
    run_count: int
    last_run_date: date | None
    is_active: bool
    template: dict


class CreatedTransaction(BaseModel):
    schedule_id: int
    schedule_name: str
    transaction_type: RecurringType
    transaction_id: int
    transaction_date: date


class RunDueResult(BaseModel):
    created: list[CreatedTransaction]
