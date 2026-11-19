from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import PaymentMethod
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel


class PaymentCreate(CleanStringsModel):
    invoice_id: int
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference_no: str | None = Field(default=None, max_length=100)
    # When empty, the money goes to "Undeposited Funds".
    deposit_account_id: int | None = None
    memo: str | None = Field(default=None, max_length=500)


class InvoiceNumberOnly(ORMModel):
    id: int
    invoice_number: str


class PaymentRead(ORMModel):
    id: int
    invoice: InvoiceNumberOnly
    customer: ContactSummary
    payment_date: date
    amount: Decimal
    payment_method: PaymentMethod
    reference_no: str | None
    deposit_account: AccountSummary
    memo: str | None
