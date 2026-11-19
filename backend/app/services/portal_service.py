"""
The customer's "view and pay" page. No login: the secret token in the link
is the only key, so it only ever shows that one invoice.
"""

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.integrations.payments import PaymentProcessor
from app.models import Invoice
from app.models.enums import InvoiceStatus
from app.repositories.company_repository import CompanyRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.sales_extras import PublicInvoice, PublicInvoiceLine
from app.services.company_service import logo_data_url
from app.services.customer_documents_service import CustomerDocumentsService, PdfFile


class PortalService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        company_repository: CompanyRepository,
        documents: CustomerDocumentsService,
        payment_processor: PaymentProcessor,
    ):
        self.invoice_repository = invoice_repository
        self.company_repository = company_repository
        self.documents = documents
        self.payment_processor = payment_processor

    def find_invoice(self, token: str) -> Invoice:
        invoice = self.invoice_repository.get_by_public_token(token)
        if invoice is None or invoice.status == InvoiceStatus.VOID:
            raise NotFoundError("This invoice link is not valid.")
        return invoice

    def get_invoice(self, token: str) -> PublicInvoice:
        invoice = self.find_invoice(token)
        company = self.company_repository.get(invoice.company_id)
        lines = []
        for line in invoice.lines:
            lines.append(PublicInvoiceLine(description=line.description, quantity=line.quantity, rate=line.rate, amount=line.amount))
        return PublicInvoice(
            company_name=company.name,
            company_email=company.email,
            company_address=company.address,
            accent_color=company.invoice_accent_color,
            logo_data_url=logo_data_url(company),
            invoice_number=invoice.invoice_number,
            customer_name=invoice.customer.display_name,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            status=invoice.status.value,
            subtotal=invoice.subtotal,
            discount_amount=invoice.discount_amount,
            shipping_amount=invoice.shipping_amount,
            total=invoice.total,
            amount_paid=invoice.amount_paid,
            balance_due=invoice.balance_due,
            memo=invoice.memo,
            currency=company.currency,
            lines=lines,
            online_payment_enabled=self.payment_processor.is_enabled() and invoice.balance_due > 0,
        )

    def get_pdf(self, token: str) -> PdfFile:
        return self.documents.render_invoice(self.find_invoice(token))

    def start_payment(self, token: str, amount) -> str:
        invoice = self.find_invoice(token)
        if invoice.balance_due <= 0:
            raise BusinessRuleError("This invoice is already paid.")
        if amount is None:
            amount = invoice.balance_due
        if amount > invoice.balance_due:
            raise BusinessRuleError("You cannot pay more than the balance due.")
        return self.payment_processor.create_checkout(invoice, amount, self.documents.public_url(invoice))
