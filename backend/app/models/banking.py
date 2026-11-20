"""
Banking: transfers, downloaded bank transactions, bank rules and reconciliations.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import BankRuleDirection, BankTransactionStatus, ReconciliationStatus


class Transfer(CompanyOwnedMixin, TimestampMixin, Base):
    """
    Money moved between two of your own accounts, e.g. savings -> checking,
    or paying the credit card bill from checking.

        Debit  to_account
        Credit from_account
    """

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_date: Mapped[date] = mapped_column(Date)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    memo: Mapped[str | None] = mapped_column(String(500))
    is_void: Mapped[bool] = mapped_column(default=False)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    from_account: Mapped[Account] = relationship(foreign_keys=[from_account_id])
    to_account: Mapped[Account] = relationship(foreign_keys=[to_account_id])


class BankTransaction(CompanyOwnedMixin, TimestampMixin, Base):
    """
    One line from a bank or credit card statement (imported file or bank feed).

    amount > 0: money into the account (deposit, card payment or refund)
    amount < 0: money out of the account (withdrawal, card charge)
    """

    __tablename__ = "bank_transactions"
    __table_args__ = (
        UniqueConstraint("company_id", "account_id", "external_id", name="uq_bank_txn_external"),
        Index("ix_bank_txn_review", "company_id", "account_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    txn_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The bank's own id (OFX FITID) or a fingerprint, so importing the same file twice adds nothing.
    external_id: Mapped[str] = mapped_column(String(100))
    # "CSV", "OFX" or "FEED"
    source: Mapped[str] = mapped_column(String(20))
    status: Mapped[BankTransactionStatus] = mapped_column(Enum(BankTransactionStatus, native_enum=False, length=20))

    # Suggestion from a bank rule (shown in the review list).
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("bank_rules.id"))
    suggested_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    suggested_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"))

    # What it became: the journal line it was matched to / created.
    journal_line_id: Mapped[int | None] = mapped_column(ForeignKey("journal_lines.id"))
    # "EXPENSE", "DEPOSIT", "TRANSFER", "CARD_CREDIT" or "MATCH"
    added_as: Mapped[str | None] = mapped_column(String(20))
    added_id: Mapped[int | None]

    account: Mapped[Account] = relationship(foreign_keys=[account_id])
    suggested_account: Mapped[Account | None] = relationship(foreign_keys=[suggested_account_id])


class BankRule(CompanyOwnedMixin, TimestampMixin, Base):
    """
    "If the description contains AMAZON and it is money out, categorize it as
    Office Supplies." Rules are tried in priority order; the first match wins.
    """

    __tablename__ = "bank_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    priority: Mapped[int] = mapped_column(default=100)
    # Empty = applies to every bank and card account.
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    direction: Mapped[BankRuleDirection] = mapped_column(Enum(BankRuleDirection, native_enum=False, length=20))
    # "ALL" = every condition must match, "ANY" = one is enough
    match_type: Mapped[str] = mapped_column(String(10), default="ALL")
    # [{"field": "description", "operator": "contains", "value": "AMAZON"}, ...]
    conditions: Mapped[list] = mapped_column(JSON)
    # What to do
    category_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"))
    # Add the transaction straight away instead of only suggesting it.
    auto_add: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    category_account: Mapped[Account] = relationship(foreign_keys=[category_account_id])


class Reconciliation(CompanyOwnedMixin, TimestampMixin, Base):
    """Checking your books against one bank or card statement."""

    __tablename__ = "reconciliations"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    statement_date: Mapped[date] = mapped_column(Date)
    # Balance of the last completed reconciliation (0 for the first one).
    beginning_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    ending_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[ReconciliationStatus] = mapped_column(Enum(ReconciliationStatus, native_enum=False, length=20))
    # Journal line ids ticked so far (while in progress).
    selected_line_ids: Mapped[list] = mapped_column(JSON, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped[Account] = relationship()
