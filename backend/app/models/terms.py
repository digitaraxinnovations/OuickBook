from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class PaymentTerm(CompanyOwnedMixin, TimestampMixin, Base):
    """An entry in the payment terms list, e.g. "Net 30" = due 30 days after the invoice date."""

    __tablename__ = "payment_terms"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_terms_company_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    due_days: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)


class NumberSequence(Base):
    """
    The next document number for each kind of document in a company
    (estimates, sales receipts, credit memos...).
    """

    __tablename__ = "number_sequences"
    __table_args__ = (UniqueConstraint("company_id", "sequence_key", name="uq_sequence_company_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(index=True)
    sequence_key: Mapped[str] = mapped_column(String(50))
    next_number: Mapped[int]
