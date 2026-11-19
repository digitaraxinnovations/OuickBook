from datetime import date

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_customer_documents_service,
    get_invoice_service,
    get_late_fee_service,
    get_payment_service,
)
from app.api.responses import pdf_response
from app.models import User
from app.models.enums import InvoiceStatus
from app.schemas.common import MessageResponse
from app.schemas.invoice import InvoiceCreate, InvoicePaymentRead, InvoiceRead, InvoiceSummary, ShareLinkResponse
from app.schemas.sales_extras import BatchResult, EmailRequest
from app.services.customer_documents_service import CustomerDocumentsService
from app.services.invoice_service import InvoiceService
from app.services.late_fee_service import LateFeeService
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


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    data: InvoiceCreate,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.create(user.company_id, data)


# ----- batch actions (also run by the daily job) -----

@router.post("/apply-late-fees", response_model=BatchResult)
def apply_late_fees(
    user: User = Depends(get_current_user),
    service: LateFeeService = Depends(get_late_fee_service),
):
    return service.apply_due(user.company_id, date.today())


@router.post("/send-reminders", response_model=BatchResult)
def send_overdue_reminders(
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    return service.send_overdue_reminders(user.company_id, date.today())


# ----- one invoice -----

@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.get(user.company_id, invoice_id)


@router.post("/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    return service.void(user.company_id, invoice_id)


@router.get("/{invoice_id}/payments", response_model=list[InvoicePaymentRead])
def list_invoice_payments(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return service.list_for_invoice(user.company_id, invoice_id)


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    return pdf_response(service.invoice_pdf(user.company_id, invoice_id))


@router.post("/{invoice_id}/email", response_model=MessageResponse)
def email_invoice(
    invoice_id: int,
    data: EmailRequest,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    service.email_invoice(user.company_id, invoice_id, data)
    return MessageResponse(message=f"Invoice sent to {data.to}.")


@router.post("/{invoice_id}/share-link", response_model=ShareLinkResponse)
def share_invoice_link(
    invoice_id: int,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    """The link customers open to view (and later pay) this invoice online."""
    return ShareLinkResponse(url=service.share_link(user.company_id, invoice_id))
