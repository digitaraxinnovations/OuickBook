"""
Company membership, invitations, the audit log and currencies.

- CompanyMember: a user's access to one company, with a role. A user can be a
                 member of several companies; `User.company_id` is the one
                 they are working in right now (the company switcher changes it).
- Invitation:    an email invite to join a company with a role.
- AuditLog:      who created, changed or deleted what, and when.
- Currency / ExchangeRate: currencies the company uses besides its home
                 currency, and their rates (home currency per 1 unit).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.enums import UserRole


class CompanyMember(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "company_members"
    __table_args__ = (UniqueConstraint("company_id", "user_id", name="uq_company_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=20))
    # The person who created the company. Cannot be removed or lose admin rights.
    is_primary_admin: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship()  # noqa: F821


class Invitation(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=20))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    """Written automatically when records are saved (see db/audit.py)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    # Empty for changes made by the daily job.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # "CREATED", "CHANGED" or "DELETED"
    action: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[int | None]
    summary: Mapped[str] = mapped_column(String(500))
    # {"field": [old, new]} for changes.
    changes: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Currency(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_currency_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(60))


class ExchangeRate(CompanyOwnedMixin, TimestampMixin, Base):
    """How much home currency 1 unit of `currency_code` was worth on a day."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("company_id", "currency_code", "rate_date", name="uq_exchange_rate_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), index=True)
    rate_date: Mapped[date] = mapped_column(Date)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8))
