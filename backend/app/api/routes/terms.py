from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_email_service, get_terms_service
from app.models import User
from app.schemas.sales_extras import EmailLogRead, PaymentTermRead, PaymentTermWrite
from app.services.email_service import EmailService
from app.services.terms_service import TermsService

router = APIRouter(tags=["Payment terms & Email log"])


@router.get("/terms", response_model=list[PaymentTermRead])
def list_terms(
    user: User = Depends(get_current_user),
    service: TermsService = Depends(get_terms_service),
):
    return service.list(user.company_id)


@router.post("/terms", response_model=PaymentTermRead, status_code=status.HTTP_201_CREATED)
def create_term(
    data: PaymentTermWrite,
    user: User = Depends(get_current_user),
    service: TermsService = Depends(get_terms_service),
):
    return service.create(user.company_id, data)


@router.put("/terms/{term_id}", response_model=PaymentTermRead)
def update_term(
    term_id: int,
    data: PaymentTermWrite,
    user: User = Depends(get_current_user),
    service: TermsService = Depends(get_terms_service),
):
    return service.update(user.company_id, term_id, data)


@router.get("/email-log", response_model=list[EmailLogRead])
def list_email_log(
    user: User = Depends(get_current_user),
    service: EmailService = Depends(get_email_service),
):
    """Every email sent (or recorded, when EMAIL_PROVIDER=log)."""
    return service.list_log(user.company_id)
