"""
Everything a customer receives: PDFs, emails, overdue reminders and the
"view and pay online" link.
"""

import secrets
from datetime import date, datetime, timedelta, timezone

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.documents import email_templates
from app.documents.pdf_builder import DocumentPdfBuilder
from app.documents.pdf_content import DOCUMENT_TITLES, invoice_document, money, nice_date, sales_document, statement_document
from app.integrations.email import OutgoingEmail
from app.models import Invoice
from app.models.enums import StatementType
from app.repositories.company_repository import CompanyRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.sales_repositories import SalesDocumentRepository
from app.schemas.sales_extras import BatchResult, EmailRequest, StatementEmailRequest
from app.services.base import BaseService
from app.services.email_service import EmailService
from app.services.statement_service import StatementService

# Do not send another reminder for the same invoice within this many days.
REMINDER_REPEAT_DAYS = 7


class PdfFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content


class CustomerDocumentsService(BaseService):
    def __init__(
        self,
        session,
        company_repository: CompanyRepository,
        invoice_repository: InvoiceRepository,
        sales_document_repository: SalesDocumentRepository,
        statement_service: StatementService,
        email_service: EmailService,
        settings: Settings,
    ):
        super().__init__(session)
        self.company_repository = company_repository
        self.invoice_repository = invoice_repository
        self.sales_document_repository = sales_document_repository
        self.statement_service = statement_service
        self.email_service = email_service
        self.settings = settings

    # ---------- PDFs ----------

    def invoice_pdf(self, company_id: int, invoice_id: int) -> PdfFile:
        invoice = self.get_invoice(company_id, invoice_id)
        return self.render_invoice(invoice)

    def render_invoice(self, invoice: Invoice) -> PdfFile:
        company = self.company_repository.get(invoice.company_id)
        content = DocumentPdfBuilder(company).build(invoice_document(invoice, company))
        return PdfFile(f"Invoice-{invoice.invoice_number}.pdf", content)

    def sales_document_pdf(self, company_id: int, document_id: int) -> PdfFile:
        record = self.get_sales_document(company_id, document_id)
        company = self.company_repository.get(company_id)
        content = DocumentPdfBuilder(company).build(sales_document(record, company))
        title = DOCUMENT_TITLES[record.doc_type].replace(" ", "")
        return PdfFile(f"{title}-{record.doc_number}.pdf", content)

    def statement_pdf(self, company_id: int, customer_id: int, statement_type: StatementType, start_date, end_date) -> PdfFile:
        statement = self.statement_service.build(company_id, customer_id, statement_type, start_date, end_date)
        company = self.company_repository.get(company_id)
        content = DocumentPdfBuilder(company).build(statement_document(statement, company))
        return PdfFile(f"Statement-{statement.end_date.isoformat()}.pdf", content)

    # ---------- emails ----------

    def email_invoice(self, company_id: int, invoice_id: int, request: EmailRequest) -> None:
        invoice = self.get_invoice(company_id, invoice_id)
        company = self.company_repository.get(company_id)
        values = self.invoice_values(invoice, company)
        pdf = self.render_invoice(invoice)

        email = OutgoingEmail(
            to=request.to,
            subject=request.subject or email_templates.INVOICE_SUBJECT.format(**values),
            body=request.message or email_templates.INVOICE_MESSAGE.format(**values),
            attachment_name=pdf.filename,
            attachment=pdf.content,
        )
        self.email_service.send(company_id, email, "INVOICE", invoice.id)
        invoice.last_emailed_at = datetime.now(timezone.utc)
        self.commit()

    def email_sales_document(self, company_id: int, document_id: int, request: EmailRequest) -> None:
        record = self.get_sales_document(company_id, document_id)
        company = self.company_repository.get(company_id)
        title = DOCUMENT_TITLES[record.doc_type]
        values = {
            "title": title,
            "title_lower": title.lower(),
            "number": record.doc_number,
            "company": company.name,
            "customer": record.customer.display_name,
            "amount": money(record.total, company.currency),
        }
        pdf = self.sales_document_pdf(company_id, document_id)
        email = OutgoingEmail(
            to=request.to,
            subject=request.subject or email_templates.DOCUMENT_SUBJECT.format(**values),
            body=request.message or email_templates.DOCUMENT_MESSAGE.format(**values),
            attachment_name=pdf.filename,
            attachment=pdf.content,
        )
        self.email_service.send(company_id, email, record.doc_type.value, record.id)
        record.last_emailed_at = datetime.now(timezone.utc)
        self.commit()

    def email_statement(self, company_id: int, customer_id: int, request: StatementEmailRequest) -> None:
        statement = self.statement_service.build(
            company_id, customer_id, request.statement_type, request.start_date, request.end_date
        )
        company = self.company_repository.get(company_id)
        values = {
            "company": company.name,
            "customer": statement.customer_name,
            "amount": money(statement.closing_balance, company.currency),
        }
        content = DocumentPdfBuilder(company).build(statement_document(statement, company))
        email = OutgoingEmail(
            to=request.to,
            subject=request.subject or email_templates.STATEMENT_SUBJECT.format(**values),
            body=request.message or email_templates.STATEMENT_MESSAGE.format(**values),
            attachment_name=f"Statement-{statement.end_date.isoformat()}.pdf",
            attachment=content,
        )
        self.email_service.send(company_id, email, "STATEMENT", customer_id)
        self.commit()

    def send_overdue_reminders(self, company_id: int, today: date) -> BatchResult:
        company = self.company_repository.get(company_id)
        if not company.reminders_enabled:
            return BatchResult(count=0, details=["Reminders are turned off in Sales settings."])

        details = []
        sent = 0
        now = datetime.now(timezone.utc)
        for invoice in self.invoice_repository.list_unpaid(company_id):
            days_late = (today - invoice.due_date).days
            if days_late < company.reminder_days_after_due or days_late <= 0:
                continue
            if invoice.last_reminder_at is not None and now - invoice.last_reminder_at < timedelta(days=REMINDER_REPEAT_DAYS):
                continue
            if not invoice.customer.email:
                details.append(f"Invoice {invoice.invoice_number}: skipped, customer has no email")
                continue

            values = self.invoice_values(invoice, company)
            email = OutgoingEmail(
                to=invoice.customer.email,
                subject=email_templates.REMINDER_SUBJECT.format(**values),
                body=email_templates.REMINDER_MESSAGE.format(**values),
            )
            self.email_service.send(company_id, email, "REMINDER", invoice.id)
            invoice.last_reminder_at = now
            sent += 1
            details.append(f"Invoice {invoice.invoice_number}: reminder sent to {invoice.customer.email}")

        self.commit()
        return BatchResult(count=sent, details=details)

    # ---------- customer link ----------

    def share_link(self, company_id: int, invoice_id: int) -> str:
        invoice = self.get_invoice(company_id, invoice_id)
        if invoice.public_token is None:
            invoice.public_token = secrets.token_urlsafe(32)
            self.commit()
        return self.public_url(invoice)

    def public_url(self, invoice: Invoice) -> str:
        return self.settings.public_app_url.rstrip("/") + "/portal/invoices/" + invoice.public_token

    # ---------- helpers ----------

    def invoice_values(self, invoice: Invoice, company) -> dict:
        link_line = ""
        if invoice.public_token is not None:
            link_line = "\nView it online: " + self.public_url(invoice) + "\n"
        return {
            "number": invoice.invoice_number,
            "company": company.name,
            "customer": invoice.customer.display_name,
            "amount": money(invoice.balance_due, company.currency),
            "due_date": nice_date(invoice.due_date),
            "link_line": link_line,
        }

    def get_invoice(self, company_id: int, invoice_id: int) -> Invoice:
        invoice = self.invoice_repository.get(company_id, invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    def get_sales_document(self, company_id: int, document_id: int):
        record = self.sales_document_repository.get(company_id, document_id)
        if record is None:
            raise NotFoundError("Sales form not found.")
        return record
