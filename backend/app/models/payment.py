"""
Customer payments.

One payment can pay several invoices (PaymentApplication) and can use
existing customer credits (CreditApplication). Money left over after
paying invoices stays with the customer as a credit (unapplied_amount).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.contact import Customer
from app.models.enums import CreditSource, PaymentMethod
from app.models.invoice import Invoice


class Payment(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date)
    # Money actually received (can be 0 when only credits are applied).
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Part of `amount` not used on any invoice yet - a credit for the customer.
    unapplied_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False, length=20))
    reference_no: Mapped[str | None] = mapped_column(String(100))
    deposit_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    memo: Mapped[str | None] = mapped_column(String(500))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    # Set when a bank deposit moves this payment out of Undeposited Funds.
    deposit_id: Mapped[int | None] = mapped_column(ForeignKey("bank_deposits.id"))

    customer: Mapped[Customer] = relationship()
    deposit_account: Mapped[Account] = relationship()
    applications: Mapped[list["PaymentApplication"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentApplication.id",
    )
    credits_used: Mapped[list["CreditApplication"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="CreditApplication.id",
    )


class PaymentApplication(Base):
    """How much of a payment (money + credits) went to one invoice."""

    __tablename__ = "payment_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment: Mapped[Payment] = relationship(back_populates="applications")
    invoice: Mapped[Invoice] = relationship()


class CreditApplication(Base):
    """A customer credit (credit memo or earlier overpayment) used inside a payment."""

    __tablename__ = "credit_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    source_type: Mapped[CreditSource] = mapped_column(Enum(CreditSource, native_enum=False, length=20))
    source_id: Mapped[int]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment: Mapped[Payment] = relationship(back_populates="credits_used")
