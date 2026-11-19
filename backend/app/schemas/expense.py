from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import PaymentMethod
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel


class ExpenseLineCreate(CleanStringsModel):
    account_id: int
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class ExpenseCreate(CleanStringsModel):
    vendor_id: int | None = None
    payment_account_id: int
    expense_date: date
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    reference_no: str | None = Field(default=None, max_length=100)
    memo: str | None = None
    lines: list[ExpenseLineCreate] = Field(min_length=1)


class ExpenseLineRead(ORMModel):
    id: int
    account: AccountSummary
    description: str | None
    amount: Decimal


class ExpenseRead(ORMModel):
    id: int
    vendor: ContactSummary | None
    payment_account: AccountSummary
    expense_date: date
    payment_method: PaymentMethod
    reference_no: str | None
    memo: str | None
    total: Decimal
    lines: list[ExpenseLineRead]
