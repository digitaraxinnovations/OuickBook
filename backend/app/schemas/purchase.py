from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PurchaseDocStatus, PurchaseDocType, TripPurpose
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel

# ---------- bills, vendor credits, purchase orders ----------


class PurchaseLineInput(CleanStringsModel):
    # A category line has an account; an item line has a product (the account comes from it).
    account_id: int | None = None
    product_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=12, decimal_places=2)
    rate: Decimal = Field(max_digits=12, decimal_places=2)
    customer_id: int | None = None


class PurchaseDocumentCreate(CleanStringsModel):
    doc_type: PurchaseDocType
    vendor_id: int
    doc_date: date
    # Bills: empty due date = from terms (bill terms, then vendor terms, then company default).
    due_date: date | None = None
    terms_id: int | None = None
    # Bills and vendor credits: the vendor's reference number. Purchase orders: numbered automatically.
    doc_number: str | None = Field(default=None, max_length=50)
    memo: str | None = None
    lines: list[PurchaseLineInput] = Field(min_length=1)


class PurchaseLineRead(ORMModel):
    id: int
    account: AccountSummary
    product_id: int | None
    description: str | None
    quantity: Decimal
    rate: Decimal
    amount: Decimal
    customer_id: int | None


class PurchaseDocumentSummary(ORMModel):
    id: int
    doc_type: PurchaseDocType
    doc_number: str | None
    vendor: ContactSummary
    doc_date: date
    due_date: date | None
    status: PurchaseDocStatus
    total: Decimal
    amount_applied: Decimal
    balance: Decimal
    is_overdue: bool


class PurchaseDocumentRead(PurchaseDocumentSummary):
    memo: str | None
    terms_id: int | None
    purchase_order_id: int | None
    lines: list[PurchaseLineRead]


class ConvertPurchaseOrderRequest(BaseModel):
    bill_date: date
    bill_number: str | None = Field(default=None, max_length=50)


# ---------- paying bills ----------


class BillApplicationInput(BaseModel):
    bill_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class VendorCreditUseInput(BaseModel):
    vendor_credit_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BillPaymentCreate(CleanStringsModel):
    vendor_id: int
    payment_date: date
    payment_account_id: int
    payment_method: PaymentMethod = PaymentMethod.CHECK
    # Checks: empty = next number for this bank account (unless printing later).
    check_number: str | None = Field(default=None, max_length=20)
    print_later: bool = False
    memo: str | None = Field(default=None, max_length=500)
    applications: list[BillApplicationInput] = Field(min_length=1)
    credits: list[VendorCreditUseInput] = Field(default_factory=list)


class BatchBillPaymentCreate(BaseModel):
    """Pay many bills at once. One payment is created per vendor."""

    payment_date: date
    payment_account_id: int
    payment_method: PaymentMethod = PaymentMethod.CHECK
    print_later: bool = False
    bills: list[BillApplicationInput] = Field(min_length=1)


class BillNumberOnly(ORMModel):
    id: int
    doc_number: str | None


class BillApplicationRead(ORMModel):
    bill: BillNumberOnly
    amount: Decimal


class VendorCreditUseRead(ORMModel):
    vendor_credit_id: int
    amount: Decimal


class BillPaymentRead(ORMModel):
    id: int
    vendor: ContactSummary
    payment_date: date
    payment_account: AccountSummary
    payment_method: PaymentMethod
    check_number: str | None
    print_later: bool
    amount: Decimal
    memo: str | None
    applications: list[BillApplicationRead]
    credits_used: list[VendorCreditUseRead]


class BillPaymentForBill(BaseModel):
    payment_id: int
    payment_date: date
    payment_method: PaymentMethod
    check_number: str | None
    payment_account: AccountSummary
    amount: Decimal


# ---------- printing checks ----------


class CheckToPrint(BaseModel):
    """A check waiting to be printed: an expense of kind CHECK or a bill payment."""

    source_type: str  # "EXPENSE" or "BILL_PAYMENT"
    source_id: int
    check_date: date
    payee: str
    bank_account: AccountSummary
    amount: Decimal


class CheckPrintItem(BaseModel):
    source_type: str = Field(pattern="^(EXPENSE|BILL_PAYMENT)$")
    source_id: int


class PrintChecksRequest(BaseModel):
    bank_account_id: int
    first_check_number: int = Field(ge=1)
    items: list[CheckPrintItem] = Field(min_length=1)


class NextCheckNumber(BaseModel):
    bank_account_id: int
    next_check_number: int


# ---------- attachments / receipts ----------


class AttachmentUpload(CleanStringsModel):
    # "RECEIPT" for the receipts inbox, or EXPENSE, BILL, INVOICE, VENDOR_CREDIT...
    entity_type: str = Field(pattern="^[A-Z_]{3,30}$")
    entity_id: int | None = None
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=100)
    data_base64: str
    note: str | None = Field(default=None, max_length=500)


class AttachmentLink(BaseModel):
    entity_type: str = Field(pattern="^[A-Z_]{3,30}$")
    entity_id: int


class AttachmentRead(ORMModel):
    id: int
    entity_type: str
    entity_id: int | None
    filename: str
    mime_type: str
    size_bytes: int
    note: str | None
    created_at: datetime


# ---------- mileage ----------


class TripWrite(CleanStringsModel):
    trip_date: date
    vehicle: str | None = Field(default=None, max_length=100)
    start_location: str | None = Field(default=None, max_length=200)
    end_location: str | None = Field(default=None, max_length=200)
    miles: Decimal = Field(gt=0, max_digits=10, decimal_places=1)
    purpose: TripPurpose = TripPurpose.BUSINESS
    notes: str | None = Field(default=None, max_length=500)


class TripRead(ORMModel):
    id: int
    trip_date: date
    vehicle: str | None
    start_location: str | None
    end_location: str | None
    miles: Decimal
    purpose: TripPurpose
    notes: str | None


class MileageSummary(BaseModel):
    year: int
    business_miles: Decimal
    personal_miles: Decimal
    rate: Decimal
    deduction: Decimal


class MileageRateUpdate(BaseModel):
    mileage_rate: Decimal = Field(ge=0, max_digits=6, decimal_places=3)
