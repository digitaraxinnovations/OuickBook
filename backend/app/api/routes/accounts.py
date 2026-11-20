from fastapi import APIRouter, Depends, status

from app.api.deps import get_account_service, get_current_user
from app.models import User
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.seed.default_accounts import FORM_1099_BOXES
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["Chart of Accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(
    active_only: bool = False,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    return service.list_with_balances(user.company_id, active_only)


@router.get("/1099-boxes", response_model=dict[str, str])
def list_1099_boxes(user: User = Depends(get_current_user)):
    """The 1099 boxes an expense account can be mapped to."""
    return FORM_1099_BOXES


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    return service.create(user.company_id, data)


@router.put("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    data: AccountUpdate,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    return service.update(user.company_id, account_id, data)
