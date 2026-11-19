from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_payment_service
from app.models import User
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=list[PaymentRead])
def list_payments(
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return service.list(user.company_id)


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def receive_payment(
    data: PaymentCreate,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return service.receive(user.company_id, data)
