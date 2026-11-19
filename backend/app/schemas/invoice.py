from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import InvoiceStatus
from app.schemas.common import CleanStringsModel, ContactSummary, ORMModel


class InvoiceLineCreate(CleanStringsModel):
    product_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    rate: Decimal = Field(max_digits=12, decimal_places=2)


class InvoiceCreate(CleanStringsModel):
    customer_id: int
    invoice_date: date
    # When empty, the company's payment terms are used (e.g. 30 days).
    due_date: date | None = None
    memo: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


class InvoiceLineRead(ORMModel):
    id: int
    product_id: int | None
    income_account_id: int
    description: str | None
    quantity: Decimal
    rate: Decimal
    amount: Decimal


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


class InvoiceRead(InvoiceSummary):
    memo: str | None
    lines: list[InvoiceLineRead]
