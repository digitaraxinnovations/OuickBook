from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin


class EmailLog(CompanyOwnedMixin, Base):
    """Every email the app sends (or would send, when no email provider is set up)."""

    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    to_address: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    attachment_name: Mapped[str | None] = mapped_column(String(200))
    # e.g. "INVOICE", "ESTIMATE", "STATEMENT", "REMINDER"
    related_type: Mapped[str | None] = mapped_column(String(30))
    related_id: Mapped[int | None]
    # Which sender handled it ("log" or "smtp") and whether it worked.
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text)
