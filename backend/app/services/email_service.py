from app.core.exceptions import BusinessRuleError
from app.integrations.email import EmailSender, OutgoingEmail
from app.models import EmailLog
from app.repositories.sales_repositories import EmailLogRepository
from app.services.base import BaseService


class EmailService(BaseService):
    """Sends an email through the configured sender and records it in the Email log."""

    def __init__(self, session, repository: EmailLogRepository, sender: EmailSender):
        super().__init__(session)
        self.repository = repository
        self.sender = sender

    def list_log(self, company_id: int) -> list[EmailLog]:
        return self.repository.list_all(company_id)

    def send(self, company_id: int, email: OutgoingEmail, related_type: str | None = None, related_id: int | None = None) -> EmailLog:
        record = EmailLog(
            company_id=company_id,
            to_address=email.to,
            subject=email.subject,
            body=email.body,
            attachment_name=email.attachment_name,
            related_type=related_type,
            related_id=related_id,
            provider=self.sender.provider_name,
            status="SENT" if self.sender.provider_name != "log" else "LOGGED",
        )
        try:
            self.sender.send(email)
        except Exception as error:
            record.status = "FAILED"
            record.error = str(error)
            self.repository.add(record)
            self.commit()
            raise BusinessRuleError(f"The email could not be sent: {error}")

        self.repository.add(record)
        return record
