"""
Ways to slice your books besides accounts.

- TrackingClass: e.g. departments or product lines ("Residential", "Commercial").
- Location:      e.g. stores, regions or offices.
- Project:       a job for one customer; its income and costs give its profit.
- Tag:           free labels you can put on any transaction ("Spring promo").
- Budget:        planned income and expense per account per month.

TrackingMixin adds the class / location / project / tags fields to a
transaction (invoice, expense, bill...). When the transaction is posted the
values are copied onto its journal lines, so every report can group by them.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import ProjectStatus


class TrackingClass(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tracking_classes"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_tracking_class_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tracking_classes.id"))
    is_active: Mapped[bool] = mapped_column(default=True)


class Location(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_location_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    is_active: Mapped[bool] = mapped_column(default=True)


class Tag(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_tag_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Tags can be grouped, e.g. group "Events" with tags "Spring fair", "Expo".
    group_name: Mapped[str | None] = mapped_column(String(100))


class Project(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, native_enum=False, length=20))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)


class TrackingMixin:
    """Class, location, project and tags on a transaction."""

    class_id: Mapped[int | None] = mapped_column(ForeignKey("tracking_classes.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    tag_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), server_default=text("'{}'"))


class Budget(CompanyOwnedMixin, TimestampMixin, Base):
    """Planned amounts for one year, optionally for one class or location."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    fiscal_year: Mapped[int]
    class_id: Mapped[int | None] = mapped_column(ForeignKey("tracking_classes.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))

    lines: Mapped[list["BudgetLine"]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetLine.id",
    )


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    # 1 = January ... 12 = December
    month: Mapped[int]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    budget: Mapped[Budget] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship()
