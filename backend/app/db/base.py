"""
Base class and shared columns for all database models.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Every model inherits from this class."""


class TimestampMixin:
    """Adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CompanyOwnedMixin:
    """
    Adds a company_id column.

    Every business record (customer, invoice, account...) belongs to exactly
    one company, and every query must filter by it so companies never see
    each other's data.
    """

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
