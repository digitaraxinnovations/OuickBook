from datetime import date

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_recurring_service
from app.models import User
from app.schemas.recurring import RecurringScheduleRead, RecurringScheduleWrite, RunDueResult
from app.services.recurring_service import RecurringService

router = APIRouter(prefix="/recurring", tags=["Recurring Transactions"])


@router.get("", response_model=list[RecurringScheduleRead])
def list_schedules(
    user: User = Depends(get_current_user),
    service: RecurringService = Depends(get_recurring_service),
):
    return service.list(user.company_id)


@router.get("/{schedule_id}", response_model=RecurringScheduleRead)
def get_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    service: RecurringService = Depends(get_recurring_service),
):
    return service.get(user.company_id, schedule_id)


@router.post("", response_model=RecurringScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: RecurringScheduleWrite,
    user: User = Depends(get_current_user),
    service: RecurringService = Depends(get_recurring_service),
):
    return service.create(user.company_id, data)


@router.put("/{schedule_id}", response_model=RecurringScheduleRead)
def update_schedule(
    schedule_id: int,
    data: RecurringScheduleWrite,
    user: User = Depends(get_current_user),
    service: RecurringService = Depends(get_recurring_service),
):
    return service.update(user.company_id, schedule_id, data)


@router.post("/run-due", response_model=RunDueResult)
def run_due_schedules(
    user: User = Depends(get_current_user),
    service: RecurringService = Depends(get_recurring_service),
):
    """Create every recurring transaction that is due up to today."""
    created = service.run_due(user.company_id, date.today())
    return RunDueResult(created=created)
