"""
Sending email (EXT).

EmailSender is the interface. The app picks an implementation from the
EMAIL_PROVIDER setting:

- "log"  -> LogEmailSender: sends nothing. The email is only saved in the
            app's Email log, so everything works without an email account.
- "smtp" -> SmtpEmailSender: really sends, using the SMTP_* settings.

To support another provider (SendGrid, Amazon SES...), write a new class
that inherits from EmailSender and add it to build_email_sender().
"""

import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

from app.core.config import Settings


class OutgoingEmail:
    def __init__(self, to: str, subject: str, body: str, attachment_name: str | None = None, attachment: bytes | None = None):
        self.to = to
        self.subject = subject
        self.body = body
        self.attachment_name = attachment_name
        self.attachment = attachment


class EmailSender(ABC):
    provider_name = ""

    @abstractmethod
    def send(self, email: OutgoingEmail) -> None:
        """Send the email. Raise an exception if it fails."""


class LogEmailSender(EmailSender):
    provider_name = "log"

    def send(self, email: OutgoingEmail) -> None:
        # Nothing leaves the app; the EmailService records it in the Email log.
        return None


class SmtpEmailSender(EmailSender):
    provider_name = "smtp"

    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, email: OutgoingEmail) -> None:
        message = EmailMessage()
        message["From"] = self.settings.email_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)
        if email.attachment is not None:
            message.add_attachment(email.attachment, maintype="application", subtype="pdf", filename=email.attachment_name)

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_username:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.send_message(message)


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "smtp":
        return SmtpEmailSender(settings)
    return LogEmailSender()
