"""
Sales tax.

- TaxAgency:  who you pay the tax to (e.g. "California Department of Tax").
              Each agency has its own liability sub-account under Sales Tax Payable.
- TaxRate:    one rate an agency charges (e.g. "CA State 6%").
- TaxCode:    what you pick on an invoice. One rate, or several added
              together (a combined rate, e.g. state 6% + county 1.25%).
- SalesTaxLine:       the tax charged on one invoice / sales form, per rate.
                      The liability report is built from these.
- SalesTaxPayment:    money paid to an agency for a filing period.
- SalesTaxAdjustment: a correction to what you owe (e.g. a discount for filing early).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account


class TaxAgency(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tax_agencies"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_tax_agency_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    # "MONTHLY", "QUARTERLY" or "YEARLY"
    filing_frequency: Mapped[str] = mapped_column(String(20))
    # Filing periods are counted from this date.
    start_date: Mapped[date] = mapped_column(Date)
    liability_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    liability_account: Mapped[Account] = relationship()


class TaxRate(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tax_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    agency_id: Mapped[int] = mapped_column(ForeignKey("tax_agencies.id"))
    # Percent, e.g. 7.2500
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    is_active: Mapped[bool] = mapped_column(default=True)

    agency: Mapped[TaxAgency] = relationship()


class TaxCode(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_tax_code_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)

    components: Mapped[list["TaxCodeRate"]] = relationship(
        back_populates="tax_code",
        cascade="all, delete-orphan",
        order_by="TaxCodeRate.id",
    )

    @property
    def total_rate(self) -> Decimal:
        total = Decimal("0")
        for component in self.components:
            total += component.tax_rate.rate
        return total


class TaxCodeRate(Base):
    """One rate inside a tax code."""

    __tablename__ = "tax_code_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_code_id: Mapped[int] = mapped_column(ForeignKey("tax_codes.id"), index=True)
    tax_rate_id: Mapped[int] = mapped_column(ForeignKey("tax_rates.id"))

    tax_code: Mapped[TaxCode] = relationship(back_populates="components")
    tax_rate: Mapped[TaxRate] = relationship()


class SalesTaxLine(CompanyOwnedMixin, Base):
    __tablename__ = "sales_tax_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    # "INVOICE" or "SALES_DOCUMENT"
    source_type: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(index=True)
    tax_date: Mapped[date] = mapped_column(Date, index=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("tax_agencies.id"), index=True)
    tax_rate_id: Mapped[int] = mapped_column(ForeignKey("tax_rates.id"))
    # Negative for credit memos and refunds (tax given back).
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_void: Mapped[bool] = mapped_column(default=False)

    tax_rate: Mapped[TaxRate] = relationship()


class SalesTaxPayment(CompanyOwnedMixin, TimestampMixin, Base):
    """
        Debit  Agency liability (you owe less)
        Credit Bank
    """

    __tablename__ = "sales_tax_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("tax_agencies.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    memo: Mapped[str | None] = mapped_column(String(500))
    # Set when the return was e-filed through the tax provider.
    confirmation_no: Mapped[str | None] = mapped_column(String(60))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    agency: Mapped[TaxAgency] = relationship()
    payment_account: Mapped[Account] = relationship()


class SalesTaxAdjustment(CompanyOwnedMixin, TimestampMixin, Base):
    """
    amount > 0: you owe more   (Debit the chosen account, Credit the agency liability)
    amount < 0: you owe less   (Debit the agency liability, Credit the chosen account)
    """

    __tablename__ = "sales_tax_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("tax_agencies.id"), index=True)
    adjustment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The other side, e.g. "Other Income" for a filing discount.
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    reason: Mapped[str] = mapped_column(String(300))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    agency: Mapped[TaxAgency] = relationship()
    account: Mapped[Account] = relationship()
