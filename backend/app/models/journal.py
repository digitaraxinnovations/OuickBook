"""
The general ledger (double-entry bookkeeping).

Every money event (invoice, payment, expense...) creates one JournalEntry.
Each entry has two or more JournalLines. The total debits must always equal
the total credits - that rule is enforced by LedgerService.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import JournalSource


class JournalEntry(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    memo: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[JournalSource] = mapped_column(Enum(JournalSource, native_enum=False, length=20))
    # Id of the invoice / payment / expense that created this entry (if any).
    source_id: Mapped[int | None]
    # Set on void / undo entries: the entry this one cancels.
    reverses_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.id",
    )


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    debit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    credit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Banking: the line was matched to a bank statement line ("C" in the register).
    cleared: Mapped[bool] = mapped_column(server_default=text("false"))
    # Set when a completed reconciliation includes this line ("R" in the register).
    reconciliation_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliations.id"), index=True)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()
