from decimal import Decimal

from sqlalchemy import LargeBinary, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(255))
    next_invoice_number: Mapped[int]
    payment_terms_days: Mapped[int]

    # ---------- invoice look (customize form style) ----------
    # "classic", "modern" or "simple"
    invoice_template: Mapped[str] = mapped_column(String(20), server_default=text("'classic'"))
    invoice_accent_color: Mapped[str] = mapped_column(String(7), server_default=text("'#059669'"))
    invoice_footer: Mapped[str | None] = mapped_column(Text)
    logo: Mapped[bytes | None] = mapped_column(LargeBinary)
    logo_mime_type: Mapped[str | None] = mapped_column(String(50))

    # ---------- late fees ----------
    late_fee_enabled: Mapped[bool] = mapped_column(server_default=text("false"))
    # "FIXED" amount or "PERCENT" of the balance due
    late_fee_type: Mapped[str] = mapped_column(String(10), server_default=text("'FIXED'"))
    late_fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    late_fee_grace_days: Mapped[int] = mapped_column(server_default=text("0"))

    # ---------- overdue reminders ----------
    reminders_enabled: Mapped[bool] = mapped_column(server_default=text("false"))
    reminder_days_after_due: Mapped[int] = mapped_column(server_default=text("3"))
