"""
Base class and shared columns for all database models.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Give every constraint a predictable name (the same names PostgreSQL picks by
# default), so database migrations can always find and drop them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Base(DeclarativeBase):
    """Every model inherits from this class."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


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
