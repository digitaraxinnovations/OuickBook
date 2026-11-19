from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_expense_service
from app.models import User
from app.schemas.expense import ExpenseCreate, ExpenseRead
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_expense_service),
):
    return service.list(user.company_id)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: int,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_expense_service),
):
    return service.get(user.company_id, expense_id)


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_expense_service),
):
    return service.create(user.company_id, data)
