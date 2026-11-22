"""
Schemas for payment terms, bank deposits, statements, email, company sales
settings and the public customer view.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DepositLineSource, StatementType
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel

# ---------- payment terms ----------


class PaymentTermWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    due_days: int = Field(ge=0, le=365)
    is_active: bool = True


class PaymentTermRead(ORMModel):
    id: int
    name: str
    due_days: int
    is_active: bool


# ---------- bank deposits ----------


class UndepositedItem(BaseModel):
    source_type: DepositLineSource
    source_id: int
    item_date: date
    customer_name: str
    reference: str
    amount: Decimal


class DepositItemInput(BaseModel):
    source_type: DepositLineSource
    source_id: int


class DepositOtherLineInput(CleanStringsModel):
    account_id: int
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class DepositCreate(CleanStringsModel):
    deposit_date: date
    bank_account_id: int
    memo: str | None = Field(default=None, max_length=500)
    items: list[DepositItemInput] = Field(default_factory=list)
    other_lines: list[DepositOtherLineInput] = Field(default_factory=list)


class DepositLineRead(ORMModel):
    id: int
    source_type: DepositLineSource
    source_id: int | None
    account: AccountSummary
    description: str | None
    amount: Decimal


class DepositRead(ORMModel):
    id: int
    deposit_date: date
    bank_account: AccountSummary
    memo: str | None
    total: Decimal
    lines: list[DepositLineRead]


# ---------- customer statements ----------


class StatementLine(BaseModel):
    line_date: date
    transaction_type: str
    reference: str
    amount: Decimal
    balance: Decimal


class StatementResult(BaseModel):
    customer_id: int
    customer_name: str
    customer_email: str | None
    customer_address: str | None
    statement_type: StatementType
    start_date: date | None
    end_date: date
    opening_balance: Decimal
    lines: list[StatementLine]
    closing_balance: Decimal


# ---------- email ----------


class EmailRequest(CleanStringsModel):
    to: EmailStr
    subject: str | None = Field(default=None, max_length=300)
    message: str | None = None


class StatementEmailRequest(EmailRequest):
    statement_type: StatementType = StatementType.BALANCE_FORWARD
    start_date: date | None = None
    end_date: date | None = None


class EmailLogRead(ORMModel):
    id: int
    sent_at: datetime
    to_address: str
    subject: str
    body: str
    attachment_name: str | None
    related_type: str | None
    related_id: int | None
    provider: str
    status: str
    error: str | None


class BatchResult(BaseModel):
    """Result of a batch job such as 'apply late fees' or 'send reminders'."""

    count: int
    details: list[str]


# ---------- company sales settings ----------


class SalesSettingsUpdate(BaseModel):
    invoice_template: str = Field(pattern="^(classic|modern|simple)$")
    invoice_accent_color: str = Field(pattern="^#[0-9a-fA-F]{6}$")
    invoice_footer: str | None = None
    late_fee_enabled: bool = False
    late_fee_type: str = Field(default="FIXED", pattern="^(FIXED|PERCENT)$")
    late_fee_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    late_fee_grace_days: int = Field(default=0, ge=0, le=365)
    reminders_enabled: bool = False
    reminder_days_after_due: int = Field(default=3, ge=0, le=365)


class SalesSettingsRead(ORMModel):
    invoice_template: str
    invoice_accent_color: str
    invoice_footer: str | None
    late_fee_enabled: bool
    late_fee_type: str
    late_fee_amount: Decimal
    late_fee_grace_days: int
    reminders_enabled: bool
    reminder_days_after_due: int


class LogoUpload(BaseModel):
    """The image as base64 text (the browser's FileReader gives this directly)."""

    mime_type: str = Field(pattern="^image/(png|jpeg)$")
    data_base64: str


class LogoRead(BaseModel):
    data_url: str | None


# ---------- public customer view ----------


class PublicInvoiceLine(BaseModel):
    description: str | None
    quantity: Decimal
    rate: Decimal
    amount: Decimal


class PublicInvoice(BaseModel):
    company_name: str
    company_email: str | None
    company_address: str | None
    accent_color: str
    logo_data_url: str | None
    invoice_number: str
    customer_name: str
    invoice_date: date
    due_date: date
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal = Decimal("0.00")
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    memo: str | None
    currency: str
    lines: list[PublicInvoiceLine]
    online_payment_enabled: bool
    # True when the checkout is the built-in simulation (no real money moves).
    online_payment_simulated: bool = False


class PayOnlineRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class PayOnlineResponse(BaseModel):
    checkout_url: str
