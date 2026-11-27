"""
Checks on what is owed: long overdue invoices and credits nobody has used.
"""

from datetime import date

from app.core.config import Settings
from app.core.money import ZERO, to_money
from app.health.base import HealthCheck
from app.models.enums import PurchaseDocStatus, PurchaseDocType
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.repositories.sales_repositories import PaymentRepository, SalesDocumentRepository
from app.schemas.health import Severity


class OverdueInvoiceCheck(HealthCheck):
    name = "Old unpaid invoices"
    severity = Severity.HIGH

    def __init__(self, settings: Settings, invoices: InvoiceRepository):
        self.settings = settings
        self.invoices = invoices

    def run(self, company_id: int, today: date):
        result = []
        for invoice in self.invoices.list_unpaid(company_id):
            days = (today - invoice.due_date).days
            if days > self.settings.health_overdue_days and invoice.balance_due > 0:
                title = f"Invoice {invoice.invoice_number} - {invoice.customer.display_name}"
                detail = f"{to_money(invoice.balance_due * invoice.exchange_rate):,.2f} is {days} days overdue."
                result.append(self.finding(f"overdue:{invoice.id}", title, detail, f"/sales/invoices/{invoice.id}"))
        return result


class UnusedCreditCheck(HealthCheck):
    name = "Unused credits"
    severity = Severity.LOW

    def __init__(
        self,
        customers: CustomerRepository,
        sales_documents: SalesDocumentRepository,
        payments: PaymentRepository,
        purchases: PurchaseDocumentRepository,
    ):
        self.customers = customers
        self.sales_documents = sales_documents
        self.payments = payments
        self.purchases = purchases

    def run(self, company_id: int, today: date):
        credits: dict[int, object] = {}
        for source in (self.sales_documents.open_credit_by_customer(company_id), self.payments.unapplied_by_customer(company_id)):
            for customer_id, amount in source.items():
                credits[customer_id] = credits.get(customer_id, ZERO) + amount

        result = []
        for customer_id, amount in credits.items():
            if amount <= 0:
                continue
            name = self.customers.get(company_id, customer_id).display_name
            result.append(
                self.finding(
                    f"customer-credit:{customer_id}:{amount}",
                    f"{name} has unused credit",
                    f"{amount:,.2f} can be applied to an invoice or refunded.",
                    f"/sales/customers/{customer_id}",
                )
            )

        for credit in self.purchases.list_filtered(company_id, doc_type=PurchaseDocType.VENDOR_CREDIT):
            if credit.status in (PurchaseDocStatus.OPEN, PurchaseDocStatus.PARTIALLY_PAID) and credit.balance > 0:
                result.append(
                    self.finding(
                        f"vendor-credit:{credit.id}:{credit.balance}",
                        f"Unused credit from {credit.vendor.display_name}",
                        f"{to_money(credit.balance * credit.exchange_rate):,.2f} can be used when paying their bills.",
                        f"/expenses/forms/vendor-credits/{credit.id}",
                    )
                )
        return result
