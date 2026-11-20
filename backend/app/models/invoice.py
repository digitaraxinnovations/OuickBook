from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.tracking import TrackingMixin
from app.models.contact import Customer
from app.models.enums import DiscountType, InvoiceStatus
from app.models.product import Product


class Invoice(TrackingMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("company_id", "invoice_number", name="uq_invoice_company_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(30))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    terms_id: Mapped[int | None] = mapped_column(ForeignKey("payment_terms.id"))
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus, native_enum=False, length=20))
    memo: Mapped[str | None] = mapped_column(Text)

    # total = subtotal - discount_amount + shipping_amount (+ late fees added later)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    discount_type: Mapped[DiscountType | None] = mapped_column(Enum(DiscountType, native_enum=False, length=10))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    tax_code_id: Mapped[int | None] = mapped_column(ForeignKey("tax_codes.id"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    # Foreign currency: amounts on this form are in `currency_code`;
    # home amount = amount x exchange_rate. Empty / 1 for the home currency.
    currency_code: Mapped[str | None] = mapped_column(String(3))
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), server_default=text("1"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    # Progress invoicing: the estimate this invoice was made from.
    estimate_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_documents.id", use_alter=True, name="fk_invoices_estimate_id")
    )
    late_fee_applied_on: Mapped[date | None] = mapped_column(Date)
    # Secret part of the customer's "view and pay" link. Empty until shared.
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    last_emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship()
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.id",
    )

    @property
    def balance_due(self) -> Decimal:
        if self.status == InvoiceStatus.VOID:
            return Decimal("0.00")
        return self.total - self.amount_paid

    @property
    def is_overdue(self) -> bool:
        return self.balance_due > 0 and self.due_date < date.today()


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    income_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Late-fee lines are added after the invoice was created.
    is_late_fee: Mapped[bool] = mapped_column(server_default=text("false"))
    taxable: Mapped[bool] = mapped_column(server_default=text("false"))

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
    product: Mapped[Product | None] = relationship()
