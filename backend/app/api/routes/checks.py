from fastapi import APIRouter, Depends

from app.api.deps import get_check_printing_service, get_current_user
from app.api.responses import pdf_response
from app.models import User
from app.schemas.purchase import CheckToPrint, NextCheckNumber, PrintChecksRequest
from app.services.check_printing_service import CheckPrintingService

router = APIRouter(prefix="/checks", tags=["Check printing"])


@router.get("/to-print", response_model=list[CheckToPrint])
def list_checks_to_print(
    user: User = Depends(get_current_user),
    service: CheckPrintingService = Depends(get_check_printing_service),
):
    return service.list_to_print(user.company_id)


@router.get("/next-number/{bank_account_id}", response_model=NextCheckNumber)
def next_check_number(
    bank_account_id: int,
    user: User = Depends(get_current_user),
    service: CheckPrintingService = Depends(get_check_printing_service),
):
    return service.next_number(user.company_id, bank_account_id)


@router.post("/print")
def print_checks(
    data: PrintChecksRequest,
    user: User = Depends(get_current_user),
    service: CheckPrintingService = Depends(get_check_printing_service),
):
    """Numbers the checks, marks them printed and returns the PDF to print."""
    return pdf_response(service.print_checks(user.company_id, data))


@router.get("/{source_type}/{source_id}/pdf")
def reprint_check(
    source_type: str,
    source_id: int,
    user: User = Depends(get_current_user),
    service: CheckPrintingService = Depends(get_check_printing_service),
):
    return pdf_response(service.reprint(user.company_id, source_type.upper(), source_id))
