from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel

# ---------- agencies, rates, codes ----------


class TaxAgencyWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    filing_frequency: str = Field(default="QUARTERLY", pattern="^(MONTHLY|QUARTERLY|YEARLY)$")
    start_date: date
    is_active: bool = True


class TaxAgencyRead(ORMModel):
    id: int
    name: str
    filing_frequency: str
    start_date: date
    liability_account: AccountSummary
    is_active: bool


class TaxRateWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    agency_id: int
    rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4)
    is_active: bool = True
    # Also make a tax code with just this rate, so it can be picked on invoices.
    create_code: bool = True


class TaxRateRead(ORMModel):
    id: int
    name: str
    agency_id: int
    rate: Decimal
    is_active: bool


class TaxCodeWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    rate_ids: list[int] = Field(min_length=1)
    is_active: bool = True


class TaxCodeComponent(BaseModel):
    tax_rate_id: int
    name: str
    rate: Decimal
    agency_id: int


class TaxCodeRead(BaseModel):
    id: int
    name: str
    is_active: bool
    total_rate: Decimal
    components: list[TaxCodeComponent]


# ---------- payments, adjustments, periods ----------


class SalesTaxPaymentCreate(CleanStringsModel):
    agency_id: int
    payment_date: date
    period_start: date
    period_end: date
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    payment_account_id: int
    memo: str | None = Field(default=None, max_length=500)


class SalesTaxPaymentRead(ORMModel):
    id: int
    agency_id: int
    payment_date: date
    period_start: date
    period_end: date
    amount: Decimal
    payment_account: AccountSummary
    memo: str | None


class SalesTaxAdjustmentCreate(CleanStringsModel):
    agency_id: int
    adjustment_date: date
    # Positive = you owe more, negative = you owe less.
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    account_id: int
    reason: str = Field(min_length=1, max_length=300)


class SalesTaxAdjustmentRead(ORMModel):
    id: int
    agency_id: int
    adjustment_date: date
    amount: Decimal
    account: AccountSummary
    reason: str


class TaxPeriod(BaseModel):
    agency_id: int
    agency_name: str
    period_start: date
    period_end: date
    tax_collected: Decimal
    adjustments: Decimal
    payments: Decimal
    balance: Decimal
    # "OPEN" (period not over), "DUE", "PAID" or "NOTHING_DUE"
    status: str


# ---------- EXT ----------


class RateLookupRequest(BaseModel):
    address: str = Field(min_length=3, max_length=300)


class RateLookupResult(BaseModel):
    name: str
    rate: Decimal
