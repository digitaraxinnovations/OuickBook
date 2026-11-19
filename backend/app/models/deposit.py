"""
Bank deposits.

Customer payments usually go to "Undeposited Funds" first. A bank deposit
moves a group of them into a real bank account, the same way you take a
pile of checks to the bank. Other money (e.g. an owner's investment) can be
added on the same deposit.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import DepositLineSource


class BankDeposit(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "bank_deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    deposit_date: Mapped[date] = mapped_column(Date)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    memo: Mapped[str | None] = mapped_column(String(500))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    bank_account: Mapped[Account] = relationship()
    lines: Mapped[list["DepositLine"]] = relationship(
        back_populates="deposit",
        cascade="all, delete-orphan",
        order_by="DepositLine.id",
    )


class DepositLine(Base):
    __tablename__ = "deposit_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    deposit_id: Mapped[int] = mapped_column(ForeignKey("bank_deposits.id"), index=True)
    source_type: Mapped[DepositLineSource] = mapped_column(Enum(DepositLineSource, native_enum=False, length=20))
    # Payment or sales receipt id (empty for OTHER lines).
    source_id: Mapped[int | None]
    # The account the money comes out of (Undeposited Funds, or any account for OTHER lines).
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    deposit: Mapped[BankDeposit] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()
