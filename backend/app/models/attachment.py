from sqlalchemy import Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class Attachment(CompanyOwnedMixin, TimestampMixin, Base):
    """
    A file (receipt photo, PDF...) attached to a transaction.

    `entity_type` + `entity_id` say what it belongs to, e.g. ("EXPENSE", 12).
    Receipts uploaded but not yet matched to anything use entity_type "RECEIPT"
    and no entity_id - that is the receipts inbox.
    """

    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_entity", "company_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int | None]
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    content: Mapped[bytes] = mapped_column(LargeBinary)
    note: Mapped[str | None] = mapped_column(String(500))
