from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_deposit_service
from app.models import User
from app.schemas.sales_extras import DepositCreate, DepositRead, UndepositedItem
from app.services.deposit_service import DepositService

router = APIRouter(prefix="/deposits", tags=["Bank Deposits"])


@router.get("", response_model=list[DepositRead])
def list_deposits(
    user: User = Depends(get_current_user),
    service: DepositService = Depends(get_deposit_service),
):
    return service.list(user.company_id)


@router.get("/undeposited", response_model=list[UndepositedItem])
def list_undeposited_funds(
    user: User = Depends(get_current_user),
    service: DepositService = Depends(get_deposit_service),
):
    """Payments and sales receipts waiting to be deposited."""
    return service.list_undeposited(user.company_id)


@router.get("/{deposit_id}", response_model=DepositRead)
def get_deposit(
    deposit_id: int,
    user: User = Depends(get_current_user),
    service: DepositService = Depends(get_deposit_service),
):
    return service.get(user.company_id, deposit_id)


@router.post("", response_model=DepositRead, status_code=status.HTTP_201_CREATED)
def create_deposit(
    data: DepositCreate,
    user: User = Depends(get_current_user),
    service: DepositService = Depends(get_deposit_service),
):
    return service.create(user.company_id, data)
