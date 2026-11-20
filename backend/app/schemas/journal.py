from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import JournalSource
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel


class JournalLineCreate(CleanStringsModel):
    account_id: int
    description: str | None = Field(default=None, max_length=500)
    debit: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    class_id: int | None = None
    location_id: int | None = None
    project_id: int | None = None


class JournalEntryCreate(CleanStringsModel):
    entry_date: date
    memo: str | None = Field(default=None, max_length=500)
    tag_ids: list[int] = Field(default_factory=list)
    lines: list[JournalLineCreate] = Field(min_length=2)


class JournalLineRead(ORMModel):
    id: int
    account: AccountSummary
    description: str | None
    debit: Decimal
    credit: Decimal
    class_id: int | None = None
    location_id: int | None = None
    project_id: int | None = None


class JournalEntryRead(ORMModel):
    id: int
    entry_date: date
    memo: str | None
    source_type: JournalSource
    source_id: int | None
    tag_ids: list[int] = Field(default_factory=list)
    lines: list[JournalLineRead]
