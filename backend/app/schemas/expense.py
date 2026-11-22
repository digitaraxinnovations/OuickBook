from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import ExpenseKind, PaymentMethod
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel
from app.schemas.tracking import TrackingInput, TrackingRead


class ExpenseLineCreate(CleanStringsModel):
    # A category line has an account; an item line has a product (the account comes from it).
    account_id: int | None = None
    product_id: int | None = None
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    # Billable to this customer.
    customer_id: int | None = None


class ExpenseCreate(TrackingInput, CleanStringsModel):
    kind: ExpenseKind = ExpenseKind.EXPENSE
    vendor_id: int | None = None
    payment_account_id: int
    expense_date: date
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    reference_no: str | None = Field(default=None, max_length=100)
    # Checks only. Empty = next number for that bank account (unless printing later).
    check_number: str | None = Field(default=None, max_length=20)
    print_later: bool = False
    memo: str | None = None
    # Foreign currency vendors: the rate for this form (empty = the latest saved rate).
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=8)
    lines: list[ExpenseLineCreate] = Field(min_length=1)


class ExpenseLineRead(ORMModel):
    id: int
    account: AccountSummary
    product_id: int | None
    quantity: Decimal
    description: str | None
    amount: Decimal
    customer_id: int | None


class ExpenseRead(TrackingRead, ORMModel):
    id: int
    kind: ExpenseKind
    vendor: ContactSummary | None
    payment_account: AccountSummary
    expense_date: date
    payment_method: PaymentMethod
    reference_no: str | None
    check_number: str | None
    print_later: bool
    memo: str | None
    total: Decimal
    currency_code: str | None = None
    exchange_rate: Decimal = Decimal("1")
    is_void: bool
    lines: list[ExpenseLineRead]
