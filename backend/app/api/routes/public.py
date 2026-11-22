"""
Public routes for customers. No login - the secret token in the link is the key.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_portal_service
from app.api.responses import pdf_response
from app.schemas.sales_extras import PayOnlineRequest, PayOnlineResponse, PublicInvoice
from app.services.portal_service import PortalService

router = APIRouter(prefix="/public", tags=["Customer view (no login)"])


@router.get("/invoices/{token}", response_model=PublicInvoice)
def view_invoice(token: str, service: PortalService = Depends(get_portal_service)):
    return service.get_invoice(token)


@router.get("/invoices/{token}/pdf")
def download_invoice_pdf(token: str, service: PortalService = Depends(get_portal_service)):
    return pdf_response(service.get_pdf(token))


@router.post("/invoices/{token}/pay", response_model=PayOnlineResponse)
def pay_invoice_online(token: str, data: PayOnlineRequest, service: PortalService = Depends(get_portal_service)):
    return PayOnlineResponse(checkout_url=service.start_payment(token, data.amount))


@router.post("/invoices/{token}/mock-pay", response_model=PublicInvoice)
def confirm_simulated_payment(token: str, data: PayOnlineRequest, service: PortalService = Depends(get_portal_service)):
    """The 'Pay' button on the simulated checkout page (only when PAYMENT_PROVIDER=mock)."""
    return service.confirm_mock_payment(token, data.amount)
