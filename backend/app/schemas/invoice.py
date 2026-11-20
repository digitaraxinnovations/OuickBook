from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import DiscountType, InvoiceStatus
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel
from app.schemas.tracking import TrackingInput, TrackingRead


class InvoiceLineCreate(CleanStringsModel):
    """One product/service line. Used by invoices and every other sales form."""

    product_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    rate: Decimal = Field(max_digits=12, decimal_places=2)
    # Empty = use the product's setting (lines without a product are taxable).
    taxable: bool | None = None


class SalesAmountsInput(TrackingInput, CleanStringsModel):
    """Discount, shipping and sales tax - shared by invoices and other sales forms."""

    tax_code_id: int | None = None
    # Foreign currency customers: home currency per 1 unit. Empty = the latest saved rate.
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=8)
    discount_type: DiscountType | None = None
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    shipping_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)


class InvoiceCreate(SalesAmountsInput):
    customer_id: int
    invoice_date: date
    # When empty, the due date comes from the terms (or the company default).
    due_date: date | None = None
    terms_id: int | None = None
    memo: str | None = None
    lines: list[InvoiceLineCreate] = Field(default_factory=list)
    # Delayed charges/credits to add to this invoice.
    delayed_document_ids: list[int] = Field(default_factory=list)
    # Billable time to add to this invoice.
    time_entry_ids: list[int] = Field(default_factory=list)
    # Money the customer pays up front when the invoice is created.
    deposit_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    deposit_account_id: int | None = None


class InvoiceLineRead(ORMModel):
    id: int
    product_id: int | None
    income_account_id: int
    description: str | None
    quantity: Decimal
    rate: Decimal
    amount: Decimal
    is_late_fee: bool = False
    taxable: bool = False


class InvoiceSummary(ORMModel):
    """Used in lists - no line items."""

    id: int
    invoice_number: str
    customer: ContactSummary
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    is_overdue: bool


class InvoiceRead(TrackingRead, InvoiceSummary):
    memo: str | None
    terms_id: int | None
    subtotal: Decimal
    discount_type: DiscountType | None
    discount_value: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_code_id: int | None
    tax_amount: Decimal
    currency_code: str | None = None
    exchange_rate: Decimal = Decimal("1")
    estimate_id: int | None
    late_fee_applied_on: date | None
    last_emailed_at: datetime | None
    lines: list[InvoiceLineRead]


class InvoicePaymentRead(ORMModel):
    """One payment as seen from an invoice: how much of it went to this invoice."""

    payment_id: int
    payment_date: date
    payment_method: str
    reference_no: str | None
    deposit_account: AccountSummary
    amount: Decimal


class ShareLinkResponse(ORMModel):
    url: str
