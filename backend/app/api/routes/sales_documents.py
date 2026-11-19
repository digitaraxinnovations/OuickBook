from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_customer_documents_service,
    get_invoice_service,
    get_sales_document_service,
)
from app.api.responses import pdf_response
from app.models import User
from app.models.enums import SalesDocStatus, SalesDocType
from app.schemas.common import MessageResponse
from app.schemas.invoice import InvoiceRead
from app.schemas.sales_document import (
    ConvertEstimateRequest,
    EstimateStatusChange,
    SalesDocumentCreate,
    SalesDocumentRead,
    SalesDocumentSummary,
)
from app.schemas.sales_extras import EmailRequest
from app.services.customer_documents_service import CustomerDocumentsService
from app.services.invoice_service import InvoiceService
from app.services.sales_document_service import SalesDocumentService

router = APIRouter(prefix="/sales-documents", tags=["Estimates, receipts, credits"])


@router.get("", response_model=list[SalesDocumentSummary])
def list_sales_documents(
    doc_type: SalesDocType | None = None,
    customer_id: int | None = None,
    status: SalesDocStatus | None = None,
    user: User = Depends(get_current_user),
    service: SalesDocumentService = Depends(get_sales_document_service),
):
    return service.list(user.company_id, doc_type, customer_id, status)


@router.post("", response_model=SalesDocumentRead, status_code=status.HTTP_201_CREATED)
def create_sales_document(
    data: SalesDocumentCreate,
    user: User = Depends(get_current_user),
    service: SalesDocumentService = Depends(get_sales_document_service),
):
    return service.create(user.company_id, data)


@router.get("/{document_id}", response_model=SalesDocumentRead)
def get_sales_document(
    document_id: int,
    user: User = Depends(get_current_user),
    service: SalesDocumentService = Depends(get_sales_document_service),
):
    return service.get(user.company_id, document_id)


@router.post("/{document_id}/void", response_model=SalesDocumentRead)
def void_sales_document(
    document_id: int,
    user: User = Depends(get_current_user),
    service: SalesDocumentService = Depends(get_sales_document_service),
):
    return service.void(user.company_id, document_id)


@router.post("/{document_id}/status", response_model=SalesDocumentRead)
def change_estimate_status(
    document_id: int,
    data: EstimateStatusChange,
    user: User = Depends(get_current_user),
    service: SalesDocumentService = Depends(get_sales_document_service),
):
    """Mark an estimate as pending, accepted or rejected."""
    return service.set_estimate_status(user.company_id, document_id, data.status)


@router.post("/{document_id}/convert-to-invoice", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def convert_estimate_to_invoice(
    document_id: int,
    data: ConvertEstimateRequest,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
):
    """Create an invoice from an estimate - all of it, or a percentage (progress invoicing)."""
    return service.create_from_estimate(user.company_id, document_id, data.invoice_date, data.percent)


@router.get("/{document_id}/pdf")
def get_sales_document_pdf(
    document_id: int,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    return pdf_response(service.sales_document_pdf(user.company_id, document_id))


@router.post("/{document_id}/email", response_model=MessageResponse)
def email_sales_document(
    document_id: int,
    data: EmailRequest,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    service.email_sales_document(user.company_id, document_id, data)
    return MessageResponse(message=f"Sent to {data.to}.")
