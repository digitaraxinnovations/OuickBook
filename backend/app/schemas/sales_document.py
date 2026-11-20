from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import DiscountType, PaymentMethod, SalesDocStatus, SalesDocType
from app.schemas.common import AccountSummary, ContactSummary, ORMModel
from app.schemas.invoice import InvoiceLineCreate, InvoiceLineRead, SalesAmountsInput


class SalesDocumentCreate(SalesAmountsInput):
    doc_type: SalesDocType
    customer_id: int
    doc_date: date
    expiration_date: date | None = None
    memo: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)
    # Sales receipt: account the money goes to (empty = Undeposited Funds).
    # Refund receipt: account the refund is paid from (required).
    money_account_id: int | None = None
    payment_method: PaymentMethod | None = None
    reference_no: str | None = Field(default=None, max_length=100)


class SalesDocumentLineRead(InvoiceLineRead):
    pass


class SalesDocumentSummary(ORMModel):
    id: int
    doc_type: SalesDocType
    doc_number: str
    customer: ContactSummary
    doc_date: date
    expiration_date: date | None
    status: SalesDocStatus
    total: Decimal
    amount_applied: Decimal
    remaining: Decimal


class SalesDocumentRead(SalesDocumentSummary):
    memo: str | None
    subtotal: Decimal
    discount_type: DiscountType | None
    discount_value: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_code_id: int | None
    tax_amount: Decimal
    money_account: AccountSummary | None
    payment_method: PaymentMethod | None
    reference_no: str | None
    invoice_id: int | None
    deposit_id: int | None
    last_emailed_at: datetime | None
    lines: list[SalesDocumentLineRead]


class EstimateStatusChange(BaseModel):
    status: SalesDocStatus


class ConvertEstimateRequest(BaseModel):
    invoice_date: date
    # Progress invoicing: bill this percentage of the estimate now.
    percent: Decimal = Field(default=Decimal("100"), gt=0, le=100)
