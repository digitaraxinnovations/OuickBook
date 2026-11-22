from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import CleanStringsModel, ORMModel

# ---------- companies and users ----------


class CompanyMembership(BaseModel):
    company_id: int
    company_name: str
    role: UserRole
    is_current: bool


class NewCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MemberRead(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: UserRole
    is_primary_admin: bool
    is_active: bool


class MemberUpdate(BaseModel):
    role: UserRole
    is_active: bool = True


class InvitationCreate(BaseModel):
    email: EmailStr
    role: UserRole


class InvitationRead(ORMModel):
    id: int
    email: str
    role: UserRole
    expires_at: datetime
    accepted_at: datetime | None


class InvitationInfo(BaseModel):
    """What someone opening an invite link sees before accepting."""

    company_name: str
    email: str
    role: UserRole
    has_account: bool


class AcceptInvitation(BaseModel):
    # Needed for a new account; ignored when the email already has one.
    full_name: str | None = Field(default=None, max_length=150)
    password: str = Field(min_length=8, max_length=72)


class RoleInfo(BaseModel):
    role: UserRole
    label: str


# ---------- audit log ----------


class AuditLogRead(ORMModel):
    id: int
    user_name: str
    action: str
    entity_type: str
    entity_id: int | None
    summary: str
    changes: dict | None
    created_at: datetime


# ---------- settings ----------


class AdvancedSettingsRead(ORMModel):
    fiscal_year_start_month: int
    accounting_method: str
    closing_date: date | None
    has_closing_password: bool
    multicurrency_enabled: bool
    currency: str
    bill_terms_days: int


class AdvancedSettingsUpdate(BaseModel):
    fiscal_year_start_month: int = Field(ge=1, le=12)
    accounting_method: str = Field(pattern="^(ACCRUAL|CASH)$")
    closing_date: date | None = None
    # Empty = keep the current password. "" with remove_closing_password = no password.
    closing_password: str | None = Field(default=None, max_length=72)
    remove_closing_password: bool = False
    multicurrency_enabled: bool = False
    bill_terms_days: int = Field(default=30, ge=0, le=365)


# ---------- currencies ----------


class CurrencyWrite(CleanStringsModel):
    code: str = Field(min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    name: str = Field(min_length=1, max_length=60)


class CurrencyRead(ORMModel):
    id: int
    code: str
    name: str
    latest_rate: Decimal | None = None
    latest_rate_date: date | None = None


class ExchangeRateWrite(BaseModel):
    currency_code: str = Field(min_length=3, max_length=3)
    rate_date: date
    rate: Decimal = Field(gt=0, max_digits=18, decimal_places=8)


class ExchangeRateRead(ORMModel):
    id: int
    currency_code: str
    rate_date: date
    rate: Decimal


# ---------- search and recent ----------


class SearchResult(BaseModel):
    kind: str
    title: str
    subtitle: str
    href: str


class RecentTransaction(BaseModel):
    entry_date: date
    type_label: str
    number: str
    name: str
    amount: Decimal
    href: str | None


# ---------- import ----------


class ImportRequest(BaseModel):
    content: str = Field(min_length=1)


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]


# ---------- notifications, API keys, webhooks ----------


class IntegrationStatus(BaseModel):
    provider: str
    enabled: bool
    # True for the built-in "mock" provider: it works, but nothing real happens (no money, no filings).
    simulated: bool


class IntegrationsRead(BaseModel):
    payments: IntegrationStatus
    bank_feed: IntegrationStatus
    tax_rates: IntegrationStatus
    payroll: IntegrationStatus


class Notification(BaseModel):
    kind: str
    # "info" or "warning"
    level: str
    message: str
    href: str


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ApiKeyRead(ORMModel):
    id: int
    name: str
    prefix: str
    last_used_at: datetime | None
    is_active: bool


class ApiKeyCreated(ApiKeyRead):
    # The full key - shown only once.
    key: str


class WebhookWrite(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    events: list[str] = Field(min_length=1)
    is_active: bool = True


class WebhookRead(ORMModel):
    id: int
    url: str
    events: list[str]
    secret: str
    is_active: bool


class WebhookDeliveryRead(ORMModel):
    id: int
    webhook_id: int
    event: str
    status: str
    response_code: int | None
    error: str | None
    created_at: datetime

