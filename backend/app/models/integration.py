"""
Connecting other software to Ledgerly.

- ApiKey:           lets a program use the REST API as a user (sent as the
                    Bearer token). Only a hash is stored; the key is shown once.
- Webhook:          a URL that is told when records change (e.g. "invoice.created").
- WebhookDelivery:  each event sent (or logged) to a webhook, with the result.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class ApiKey(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The program acts as this user (with their role).
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    # First characters, shown so the user can tell keys apart.
    prefix: Mapped[str] = mapped_column(String(12))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)


class Webhook(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500))
    # e.g. ["invoice.created", "payment.created"]; ["*"] = everything.
    events: Mapped[list] = mapped_column(JSON)
    # Used to sign each delivery (X-Ledgerly-Signature) so the receiver can trust it.
    secret: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(default=True)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("webhooks.id", ondelete="CASCADE"), index=True)
    event: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)
    # "SENT", "FAILED" or "LOGGED" (WEBHOOK_DELIVERY=log)
    status: Mapped[str] = mapped_column(String(10))
    response_code: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
