"""
Sales forms other than invoices: estimates, sales receipts, credit memos,
refund receipts, delayed charges and delayed credits.

They all have the same shape (a customer, a date and product lines),
so they share one table. `doc_type` says which form it is.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.contact import Customer
from app.models.enums import DiscountType, PaymentMethod, SalesDocStatus, SalesDocType
from app.models.product import Product


class SalesDocument(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "sales_documents"
    __table_args__ = (UniqueConstraint("company_id", "doc_type", "doc_number", name="uq_sales_doc_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[SalesDocType] = mapped_column(Enum(SalesDocType, native_enum=False, length=30), index=True)
    doc_number: Mapped[str] = mapped_column(String(30))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    doc_date: Mapped[date] = mapped_column(Date)
    # Estimates only: the date the offer runs out.
    expiration_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[SalesDocStatus] = mapped_column(Enum(SalesDocStatus, native_enum=False, length=20))
    memo: Mapped[str | None] = mapped_column(Text)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_type: Mapped[DiscountType | None] = mapped_column(Enum(DiscountType, native_enum=False, length=10))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Estimates: how much has been invoiced so far (progress invoicing).
    # Credit memos: how much of the credit has been used.
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    # Sales receipts: where the money went. Refund receipts: where the money came from.
    money_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    payment_method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod, native_enum=False, length=20))
    reference_no: Mapped[str | None] = mapped_column(String(100))

    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    # Delayed charges/credits: the invoice they were added to.
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    # Sales receipts paid into Undeposited Funds: the bank deposit that picked them up.
    deposit_id: Mapped[int | None] = mapped_column(ForeignKey("bank_deposits.id"))
    last_emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship()
    money_account: Mapped[Account | None] = relationship()
    lines: Mapped[list["SalesDocumentLine"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="SalesDocumentLine.id",
    )

    @property
    def remaining(self) -> Decimal:
        """Estimates: amount not yet invoiced. Credit memos: credit not yet used."""
        if self.status == SalesDocStatus.VOID:
            return Decimal("0.00")
        return self.total - self.amount_applied


class SalesDocumentLine(Base):
    __tablename__ = "sales_document_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("sales_documents.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    income_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    document: Mapped[SalesDocument] = relationship(back_populates="lines")
    product: Mapped[Product | None] = relationship()
