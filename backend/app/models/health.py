from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class HealthDismissal(CompanyOwnedMixin, TimestampMixin, Base):
    """A books health check finding the user marked "this is fine"."""

    __tablename__ = "health_dismissals"
    __table_args__ = (UniqueConstraint("company_id", "finding_key", name="uq_health_dismissal_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_key: Mapped[str] = mapped_column(String(200))
