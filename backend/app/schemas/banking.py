from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import BankRuleDirection, BankTransactionStatus, ReconciliationStatus
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel

# ---------- transfers ----------


class TransferCreate(CleanStringsModel):
    transfer_date: date
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    memo: str | None = Field(default=None, max_length=500)


class TransferRead(ORMModel):
    id: int
    transfer_date: date
    from_account: AccountSummary
    to_account: AccountSummary
    amount: Decimal
    memo: str | None
    is_void: bool


# ---------- banking overview ----------


class BankAccountOverview(BaseModel):
    account: AccountSummary
    detail_type: str
    books_balance: Decimal
    for_review_count: int
    last_imported: date | None
    last_reconciled: date | None


# ---------- import ----------


class StatementImportRequest(BaseModel):
    account_id: int
    filename: str = Field(min_length=1, max_length=255)
    # The file's text. CSV, OFX and QFX files are plain text.
    content: str
    # CSV only - column names. Leave empty to detect them from the header row.
    date_column: str | None = None
    description_column: str | None = None
    amount_column: str | None = None
    debit_column: str | None = None
    credit_column: str | None = None
    # CSV only - e.g. "%m/%d/%Y". Empty = try the common formats.
    date_format: str | None = None
    # CSV only - true if the file shows money out as positive numbers (many card statements do).
    reverse_signs: bool = False


class StatementImportResult(BaseModel):
    imported: int
    duplicates: int
    auto_added: int


# ---------- review queue ----------


class BankTransactionRead(ORMModel):
    id: int
    account_id: int
    txn_date: date
    description: str
    amount: Decimal
    source: str
    status: BankTransactionStatus
    rule_id: int | None
    suggested_account: AccountSummary | None
    suggested_vendor_id: int | None
    journal_line_id: int | None
    added_as: str | None
    added_id: int | None


class MatchCandidate(BaseModel):
    journal_line_id: int
    entry_date: date
    description: str
    amount: Decimal


class MatchRequest(BaseModel):
    journal_line_id: int


class AddLineInput(CleanStringsModel):
    account_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)


class AddTransactionRequest(CleanStringsModel):
    """Categorize a bank line. Several lines = a split."""

    vendor_id: int | None = None
    memo: str | None = Field(default=None, max_length=500)
    lines: list[AddLineInput] = Field(min_length=1)


class BatchActionResult(BaseModel):
    count: int


# ---------- rules ----------


class RuleCondition(BaseModel):
    field: str = Field(pattern="^(description|amount)$")
    operator: str = Field(pattern="^(contains|not_contains|equals|starts_with|ends_with|greater_than|less_than)$")
    value: str = Field(min_length=1, max_length=200)


class BankRuleWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    priority: int = Field(default=100, ge=1, le=9999)
    account_id: int | None = None
    direction: BankRuleDirection = BankRuleDirection.MONEY_OUT
    match_type: str = Field(default="ALL", pattern="^(ALL|ANY)$")
    conditions: list[RuleCondition] = Field(min_length=1)
    category_account_id: int
    vendor_id: int | None = None
    auto_add: bool = False
    is_active: bool = True


class BankRuleRead(ORMModel):
    id: int
    name: str
    priority: int
    account_id: int | None
    direction: BankRuleDirection
    match_type: str
    conditions: list[RuleCondition]
    category_account: AccountSummary
    vendor_id: int | None
    auto_add: bool
    is_active: bool


# ---------- reconciliation ----------


class ReconciliationStart(BaseModel):
    account_id: int
    statement_date: date
    ending_balance: Decimal = Field(max_digits=12, decimal_places=2)


class ReconciliationSelection(BaseModel):
    journal_line_ids: list[int]


class ReconcileItem(BaseModel):
    journal_line_id: int
    entry_date: date
    transaction_type: str
    description: str
    # Positive = increases the statement balance (deposits for a bank, charges for a card).
    amount: Decimal
    selected: bool


class ReconciliationRead(ORMModel):
    id: int
    account: AccountSummary
    statement_date: date
    beginning_balance: Decimal
    ending_balance: Decimal
    status: ReconciliationStatus
    completed_at: datetime | None


class ReconciliationWorkspace(BaseModel):
    reconciliation: ReconciliationRead
    items: list[ReconcileItem]
    cleared_balance: Decimal
    difference: Decimal


class ReconciliationReport(BaseModel):
    reconciliation: ReconciliationRead
    cleared_increases: list[ReconcileItem]
    cleared_decreases: list[ReconcileItem]
    cleared_balance: Decimal
    uncleared: list[ReconcileItem]
    register_balance: Decimal


class DiscrepancyItem(BaseModel):
    reconciliation_id: int
    statement_date: date
    entry_date: date
    description: str
    amount: Decimal
    changed_on: date
    change: str
