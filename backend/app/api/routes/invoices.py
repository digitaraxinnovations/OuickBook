from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_invoice_service, get_payment_service
from app.models import User
from app.models.enums import InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceSummary
from app.schemas.payment import PaymentRead
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=list[InvoiceSummary])
def list_invoices(
    customer_id: int | None = None,
    status: InvoiceStatus | None = None,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.list(user.company_id, customer_id, status)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.get(user.company_id, invoice_id)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    data: InvoiceCreate,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.create(user.company_id, data)


@router.post("/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.void(user.company_id, invoice_id)


@router.get("/{invoice_id}/payments", response_model=list[PaymentRead])
def list_invoice_payments(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return service.list_for_invoice(user.company_id, invoice_id)
