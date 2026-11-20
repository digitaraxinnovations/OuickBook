"""
Customers and vendors share the same contact fields,
so they both use ContactMixin instead of repeating the columns.
"""

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class ContactMixin:
    display_name: Mapped[str] = mapped_column(String(200))
    # Empty = the company's home currency.
    currency_code: Mapped[str | None] = mapped_column(String(3))
    company_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)


class Customer(ContactMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Default payment terms for this customer's invoices (e.g. Net 15).
    terms_id: Mapped[int | None] = mapped_column(ForeignKey("payment_terms.id"))
    # Sales tax
    tax_exempt: Mapped[bool] = mapped_column(server_default=text("false"))
    exemption_reason: Mapped[str | None] = mapped_column(String(200))
    default_tax_code_id: Mapped[int | None] = mapped_column(ForeignKey("tax_codes.id"))


class Vendor(ContactMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Default payment terms for this vendor's bills.
    terms_id: Mapped[int | None] = mapped_column(ForeignKey("payment_terms.id"))
    # Contractors you send a 1099 form to at year end.
    track_1099: Mapped[bool] = mapped_column(server_default=text("false"))
    tax_id: Mapped[str | None] = mapped_column(String(30))
