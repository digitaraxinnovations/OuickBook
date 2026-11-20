from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.enums import TripPurpose


class Trip(CompanyOwnedMixin, TimestampMixin, Base):
    """One trip in the mileage log. Business miles count toward the mileage deduction."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_date: Mapped[date] = mapped_column(Date, index=True)
    vehicle: Mapped[str | None] = mapped_column(String(100))
    start_location: Mapped[str | None] = mapped_column(String(200))
    end_location: Mapped[str | None] = mapped_column(String(200))
    miles: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    purpose: Mapped[TripPurpose] = mapped_column(Enum(TripPurpose, native_enum=False, length=20))
    notes: Mapped[str | None] = mapped_column(String(500))
