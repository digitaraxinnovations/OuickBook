"""
Customer statements.

- BALANCE_FORWARD: balance at the start date, then every transaction in the period.
- TRANSACTION:     every transaction in the period, without an opening balance.
- OPEN_ITEM:       only the invoices still unpaid on the end date.
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models.enums import InvoiceStatus, SalesDocStatus, SalesDocType, StatementType
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.sales_repositories import PaymentRepository, SalesDocumentRepository
from app.schemas.sales_extras import StatementLine, StatementResult


class Activity:
    """One thing that changed what the customer owes."""

    def __init__(self, activity_date: date, transaction_type: str, reference: str, amount):
        self.activity_date = activity_date
        self.transaction_type = transaction_type
        self.reference = reference
        self.amount = amount


class StatementService:
    def __init__(
        self,
        customer_repository: CustomerRepository,
        invoice_repository: InvoiceRepository,
        payment_repository: PaymentRepository,
        sales_document_repository: SalesDocumentRepository,
    ):
        self.customer_repository = customer_repository
        self.invoice_repository = invoice_repository
        self.payment_repository = payment_repository
        self.sales_document_repository = sales_document_repository

    def build(
        self,
        company_id: int,
        customer_id: int,
        statement_type: StatementType,
        start_date: date | None,
        end_date: date | None,
    ) -> StatementResult:
        customer = self.customer_repository.get(company_id, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found.")
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(end_date.year, end_date.month, 1)
        if start_date > end_date:
            raise BusinessRuleError("The start date must be on or before the end date.")

        if statement_type == StatementType.OPEN_ITEM:
            return self.open_item_statement(company_id, customer, end_date)

        activities = self.all_activity(company_id, customer.id, end_date)
        opening = ZERO
        lines = []
        balance = ZERO
        if statement_type == StatementType.BALANCE_FORWARD:
            for activity in activities:
                if activity.activity_date < start_date:
                    opening += activity.amount
            balance = opening

        for activity in activities:
            if activity.activity_date < start_date:
                continue
            balance += activity.amount
            lines.append(
                StatementLine(
                    line_date=activity.activity_date,
                    transaction_type=activity.transaction_type,
                    reference=activity.reference,
                    amount=activity.amount,
                    balance=balance,
                )
            )

        return StatementResult(
            customer_id=customer.id,
            customer_name=customer.display_name,
            customer_email=customer.email,
            customer_address=customer.address,
            statement_type=statement_type,
            start_date=start_date,
            end_date=end_date,
            opening_balance=opening,
            lines=lines,
            closing_balance=balance,
        )

    def all_activity(self, company_id: int, customer_id: int, end_date: date) -> list[Activity]:
        activities = []
        for invoice in self.invoice_repository.list_filtered(company_id, customer_id=customer_id):
            if invoice.status != InvoiceStatus.VOID and invoice.invoice_date <= end_date:
                activities.append(Activity(invoice.invoice_date, "Invoice", invoice.invoice_number, invoice.total))
        for payment in self.payment_repository.list_for_customer(company_id, customer_id):
            if payment.amount > 0 and payment.payment_date <= end_date:
                reference = payment.reference_no or ("#" + str(payment.id))
                activities.append(Activity(payment.payment_date, "Payment", reference, -payment.amount))
        for memo in self.sales_document_repository.list_filtered(company_id, SalesDocType.CREDIT_MEMO, customer_id):
            if memo.status != SalesDocStatus.VOID and memo.doc_date <= end_date:
                activities.append(Activity(memo.doc_date, "Credit memo", memo.doc_number, -memo.total))
        activities.sort(key=lambda activity: activity.activity_date)
        return activities

    def open_item_statement(self, company_id: int, customer, end_date: date) -> StatementResult:
        lines = []
        balance = ZERO
        invoices = self.invoice_repository.list_filtered(company_id, customer_id=customer.id)
        invoices.sort(key=lambda invoice: invoice.invoice_date)
        for invoice in invoices:
            if invoice.invoice_date > end_date or invoice.balance_due <= 0:
                continue
            balance += invoice.balance_due
            lines.append(
                StatementLine(
                    line_date=invoice.invoice_date,
                    transaction_type="Invoice (due " + invoice.due_date.isoformat() + ")",
                    reference=invoice.invoice_number,
                    amount=invoice.balance_due,
                    balance=balance,
                )
            )
        return StatementResult(
            customer_id=customer.id,
            customer_name=customer.display_name,
            customer_email=customer.email,
            customer_address=customer.address,
            statement_type=StatementType.OPEN_ITEM,
            start_date=None,
            end_date=end_date,
            opening_balance=ZERO,
            lines=lines,
            closing_balance=balance,
        )
