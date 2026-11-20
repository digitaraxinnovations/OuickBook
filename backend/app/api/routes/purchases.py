from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_bill_payment_service, get_current_user, get_purchase_service
from app.models import User
from app.models.enums import PurchaseDocStatus, PurchaseDocType
from app.schemas.purchase import (
    BatchBillPaymentCreate,
    BillPaymentCreate,
    BillPaymentForBill,
    BillPaymentRead,
    ConvertPurchaseOrderRequest,
    PurchaseDocumentCreate,
    PurchaseDocumentRead,
    PurchaseDocumentSummary,
)
from app.services.bill_payment_service import BillPaymentService
from app.services.purchase_document_service import PurchaseDocumentService

router = APIRouter(tags=["Bills, vendor credits, purchase orders"])


# ---------- bills, vendor credits, purchase orders ----------

@router.get("/purchase-documents", response_model=list[PurchaseDocumentSummary])
def list_purchase_documents(
    doc_type: PurchaseDocType | None = None,
    vendor_id: int | None = None,
    status: PurchaseDocStatus | None = None,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.list(user.company_id, doc_type, vendor_id, status)


@router.post("/purchase-documents", response_model=PurchaseDocumentRead, status_code=status.HTTP_201_CREATED)
def create_purchase_document(
    data: PurchaseDocumentCreate,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.create(user.company_id, data)


@router.get("/purchase-documents/{document_id}", response_model=PurchaseDocumentRead)
def get_purchase_document(
    document_id: int,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.get(user.company_id, document_id)


@router.post("/purchase-documents/{document_id}/void", response_model=PurchaseDocumentRead)
def void_purchase_document(
    document_id: int,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.void(user.company_id, document_id)


@router.post("/purchase-documents/{document_id}/convert-to-bill", response_model=PurchaseDocumentRead, status_code=status.HTTP_201_CREATED)
def convert_purchase_order(
    document_id: int,
    data: ConvertPurchaseOrderRequest,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.convert_purchase_order(user.company_id, document_id, data.bill_date, data.bill_number)


@router.post("/purchase-documents/{document_id}/close", response_model=PurchaseDocumentRead)
def close_purchase_order(
    document_id: int,
    user: User = Depends(get_current_user),
    service: PurchaseDocumentService = Depends(get_purchase_service),
):
    return service.close_purchase_order(user.company_id, document_id)


@router.get("/purchase-documents/{document_id}/payments", response_model=list[BillPaymentForBill])
def list_bill_payments_for_bill(
    document_id: int,
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    return service.list_for_bill(user.company_id, document_id)


# ---------- bill payments ----------

@router.get("/bill-payments", response_model=list[BillPaymentRead])
def list_bill_payments(
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    return service.list(user.company_id)


@router.post("/bill-payments", response_model=BillPaymentRead, status_code=status.HTTP_201_CREATED)
def pay_bills_of_one_vendor(
    data: BillPaymentCreate,
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    return service.pay(user.company_id, data)


@router.post("/bill-payments/batch", response_model=list[BillPaymentRead], status_code=status.HTTP_201_CREATED)
def pay_many_bills(
    data: BatchBillPaymentCreate,
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    """The "Pay bills" screen: one payment per vendor."""
    return service.pay_batch(user.company_id, data)


@router.get("/bill-payments/{payment_id}", response_model=BillPaymentRead)
def get_bill_payment(
    payment_id: int,
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    return service.get(user.company_id, payment_id)


@router.delete("/bill-payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill_payment(
    payment_id: int,
    user: User = Depends(get_current_user),
    service: BillPaymentService = Depends(get_bill_payment_service),
):
    service.delete(user.company_id, payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
