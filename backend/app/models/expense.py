from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.contact import Vendor
from app.models.enums import PaymentMethod


class Expense(CompanyOwnedMixin, TimestampMixin, Base):
    """Money paid out right away from a bank or credit card account."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), index=True)
    payment_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    expense_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False, length=20))
    reference_no: Mapped[str | None] = mapped_column(String(100))
    memo: Mapped[str | None] = mapped_column(Text)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    vendor: Mapped[Vendor | None] = relationship()
    payment_account: Mapped[Account] = relationship()
    lines: Mapped[list["ExpenseLine"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
        order_by="ExpenseLine.id",
    )


class ExpenseLine(Base):
    __tablename__ = "expense_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), index=True)
    # The category, e.g. "Rent & Lease" or "Office Supplies".
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    expense: Mapped[Expense] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()
