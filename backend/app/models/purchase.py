"""
Vendor forms and bill payments.

Bills, vendor credits and purchase orders share one table (`doc_type`
says which). A bill payment pays one or more bills of one vendor and can
use that vendor's credits.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.tracking import TrackingMixin
from app.models.account import Account
from app.models.contact import Vendor
from app.models.enums import PaymentMethod, PurchaseDocStatus, PurchaseDocType


class PurchaseDocument(TrackingMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "purchase_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[PurchaseDocType] = mapped_column(Enum(PurchaseDocType, native_enum=False, length=20), index=True)
    # Bills / vendor credits: the vendor's own reference number. Purchase orders: our number.
    doc_number: Mapped[str | None] = mapped_column(String(50))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    doc_date: Mapped[date] = mapped_column(Date)
    # Bills only
    due_date: Mapped[date | None] = mapped_column(Date)
    terms_id: Mapped[int | None] = mapped_column(ForeignKey("payment_terms.id"))
    status: Mapped[PurchaseDocStatus] = mapped_column(Enum(PurchaseDocStatus, native_enum=False, length=20))
    memo: Mapped[str | None] = mapped_column(Text)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Bills: amount paid. Vendor credits: amount used. Purchase orders: amount billed.
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    # Bills made from a purchase order.
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_documents.id"))

    vendor: Mapped[Vendor] = relationship()
    lines: Mapped[list["PurchaseDocumentLine"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PurchaseDocumentLine.id",
    )

    @property
    def balance(self) -> Decimal:
        """Bills: still to pay. Vendor credits: credit left. Purchase orders: not billed yet."""
        if self.status == PurchaseDocStatus.VOID:
            return Decimal("0.00")
        return self.total - self.amount_applied

    @property
    def is_overdue(self) -> bool:
        return self.doc_type == PurchaseDocType.BILL and self.due_date is not None and self.balance > 0 and self.due_date < date.today()


class PurchaseDocumentLine(Base):
    __tablename__ = "purchase_document_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("purchase_documents.id"), index=True)
    # The category, e.g. "Office Supplies" or "Cost of Goods Sold".
    # For an inventory item this is its Inventory Asset account.
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    # Set on "item details" lines (a product or service bought).
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1"))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Billable to a customer (shown so it can be added to an invoice later).
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))

    document: Mapped[PurchaseDocument] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()


class BillPayment(CompanyOwnedMixin, TimestampMixin, Base):
    """Money paid to a vendor for one or more bills."""

    __tablename__ = "bill_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date)
    # Bank (check, transfer) or credit card account the money came from.
    payment_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False, length=20))
    check_number: Mapped[str | None] = mapped_column(String(20))
    print_later: Mapped[bool] = mapped_column(default=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    memo: Mapped[str | None] = mapped_column(String(500))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    vendor: Mapped[Vendor] = relationship()
    payment_account: Mapped[Account] = relationship()
    applications: Mapped[list["BillPaymentApplication"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="BillPaymentApplication.id",
    )
    credits_used: Mapped[list["VendorCreditUse"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="VendorCreditUse.id",
    )


class BillPaymentApplication(Base):
    __tablename__ = "bill_payment_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("bill_payments.id"), index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("purchase_documents.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment: Mapped[BillPayment] = relationship(back_populates="applications")
    bill: Mapped[PurchaseDocument] = relationship()


class VendorCreditUse(Base):
    __tablename__ = "vendor_credit_uses"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("bill_payments.id"), index=True)
    vendor_credit_id: Mapped[int] = mapped_column(ForeignKey("purchase_documents.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment: Mapped[BillPayment] = relationship(back_populates="credits_used")
    vendor_credit: Mapped[PurchaseDocument] = relationship()
