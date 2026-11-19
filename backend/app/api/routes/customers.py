from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_customer_service
from app.models import User
from app.schemas.contact import ContactWrite, CustomerRead
from app.services.contact_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    active_only: bool = False,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    return service.list_with_balances(user.company_id, active_only)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    return service.get_with_balance(user.company_id, customer_id)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: ContactWrite,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    return service.create(user.company_id, data)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    data: ContactWrite,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    service.update(user.company_id, customer_id, data)
    return service.get_with_balance(user.company_id, customer_id)
