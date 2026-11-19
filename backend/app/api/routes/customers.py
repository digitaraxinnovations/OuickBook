from datetime import date

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_customer_documents_service,
    get_customer_service,
    get_payment_service,
    get_statement_service,
)
from app.api.responses import pdf_response
from app.models import User
from app.models.enums import StatementType
from app.schemas.common import MessageResponse
from app.schemas.contact import CustomerRead, CustomerWrite
from app.schemas.payment import CustomerCredit
from app.schemas.sales_extras import StatementEmailRequest, StatementResult
from app.services.contact_service import CustomerService
from app.services.customer_documents_service import CustomerDocumentsService
from app.services.payment_service import PaymentService
from app.services.statement_service import StatementService

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
    data: CustomerWrite,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    customer = service.create(user.company_id, data)
    return service.get_with_balance(user.company_id, customer.id)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    data: CustomerWrite,
    user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    service.update(user.company_id, customer_id, data)
    return service.get_with_balance(user.company_id, customer_id)


@router.get("/{customer_id}/credits", response_model=list[CustomerCredit])
def list_customer_credits(
    customer_id: int,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    """Open credit memos and unused overpayments this customer can apply."""
    return service.list_customer_credits(user.company_id, customer_id)


@router.get("/{customer_id}/statement", response_model=StatementResult)
def get_statement(
    customer_id: int,
    statement_type: StatementType = StatementType.BALANCE_FORWARD,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    service: StatementService = Depends(get_statement_service),
):
    return service.build(user.company_id, customer_id, statement_type, start_date, end_date)


@router.get("/{customer_id}/statement/pdf")
def get_statement_pdf(
    customer_id: int,
    statement_type: StatementType = StatementType.BALANCE_FORWARD,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    return pdf_response(service.statement_pdf(user.company_id, customer_id, statement_type, start_date, end_date))


@router.post("/{customer_id}/statement/email", response_model=MessageResponse)
def email_statement(
    customer_id: int,
    data: StatementEmailRequest,
    user: User = Depends(get_current_user),
    service: CustomerDocumentsService = Depends(get_customer_documents_service),
):
    service.email_statement(user.company_id, customer_id, data)
    return MessageResponse(message=f"Statement sent to {data.to}.")
