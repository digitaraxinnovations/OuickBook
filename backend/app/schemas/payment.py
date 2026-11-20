from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import CreditSource, PaymentMethod
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel


class PaymentApplicationInput(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class CreditUseInput(BaseModel):
    source_type: CreditSource
    source_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentCreate(CleanStringsModel):
    customer_id: int
    payment_date: date
    # Money received. Can be 0 when only credits are used to pay invoices.
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference_no: str | None = Field(default=None, max_length=100)
    # When empty, the money goes to "Undeposited Funds".
    deposit_account_id: int | None = None
    memo: str | None = Field(default=None, max_length=500)
    # Foreign currency customers: home currency per 1 unit on the payment date. Empty = latest saved rate.
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=8)
    applications: list[PaymentApplicationInput] = Field(default_factory=list)
    credits: list[CreditUseInput] = Field(default_factory=list)


class InvoiceNumberOnly(ORMModel):
    id: int
    invoice_number: str


class PaymentApplicationRead(ORMModel):
    invoice: InvoiceNumberOnly
    amount: Decimal


class CreditUseRead(ORMModel):
    source_type: CreditSource
    source_id: int
    amount: Decimal


class PaymentRead(ORMModel):
    id: int
    customer: ContactSummary
    payment_date: date
    amount: Decimal
    unapplied_amount: Decimal
    payment_method: PaymentMethod
    reference_no: str | None
    currency_code: str | None = None
    exchange_rate: Decimal = Decimal("1")
    deposit_account: AccountSummary
    memo: str | None
    deposit_id: int | None
    applications: list[PaymentApplicationRead]
    credits_used: list[CreditUseRead]


class CustomerCredit(BaseModel):
    """A credit the customer can use: an open credit memo or an overpayment."""

    source_type: CreditSource
    source_id: int
    reference: str
    credit_date: date
    remaining: Decimal
