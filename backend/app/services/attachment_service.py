"""
Attachments and the receipts inbox.

Receipts are uploaded first with entity_type "RECEIPT" (the inbox), then
linked to the expense or bill they belong to. Files can also be attached
straight to any transaction.

Reading the amount and vendor off a receipt photo automatically (OCR) needs
an outside service (EXT) and is not done here.
"""

import base64
import binascii

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Attachment
from app.repositories.purchase_repositories import AttachmentRepository
from app.schemas.purchase import AttachmentLink, AttachmentUpload
from app.services.base import BaseService

RECEIPT_INBOX = "RECEIPT"
ALLOWED_TYPES = ("image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf", "text/plain", "text/csv")


class AttachmentService(BaseService):
    def __init__(self, session, repository: AttachmentRepository, max_bytes: int):
        super().__init__(session)
        self.repository = repository
        self.max_bytes = max_bytes

    def list_for(self, company_id: int, entity_type: str, entity_id: int | None) -> list[Attachment]:
        return self.repository.list_for(company_id, entity_type, entity_id)

    def list_inbox(self, company_id: int) -> list[Attachment]:
        return self.repository.list_for(company_id, RECEIPT_INBOX, None)

    def get(self, company_id: int, attachment_id: int) -> Attachment:
        attachment = self.repository.get(company_id, attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found.")
        return attachment

    def upload(self, company_id: int, data: AttachmentUpload) -> Attachment:
        if data.mime_type not in ALLOWED_TYPES:
            raise BusinessRuleError("Only images, PDF, text and CSV files can be attached.")
        try:
            content = base64.b64decode(data.data_base64, validate=True)
        except (ValueError, binascii.Error):
            raise BusinessRuleError("The file could not be read.")
        if len(content) > self.max_bytes:
            raise BusinessRuleError(f"The file is too large. The limit is {self.max_bytes // 1_000_000} MB.")

        attachment = Attachment(
            company_id=company_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            filename=data.filename,
            mime_type=data.mime_type,
            size_bytes=len(content),
            content=content,
            note=data.note,
        )
        self.repository.add(attachment)
        self.commit()
        return attachment

    def link(self, company_id: int, attachment_id: int, data: AttachmentLink) -> Attachment:
        """Move a receipt from the inbox onto a transaction (or from one transaction to another)."""
        attachment = self.get(company_id, attachment_id)
        attachment.entity_type = data.entity_type
        attachment.entity_id = data.entity_id
        self.commit()
        return attachment

    def delete(self, company_id: int, attachment_id: int) -> None:
        attachment = self.get(company_id, attachment_id)
        self.session.delete(attachment)
        self.commit()
