"""
Recurring invoices and recurring sales receipts.

A template is the normal create request without its date. When the
schedule runs, the date is filled in and the normal service creates it.
"""

from datetime import date
from types import SimpleNamespace

from pydantic import Field, ValidationError

from app.core.exceptions import BusinessRuleError
from app.core.money import to_money
from app.models.enums import RecurringType, SalesDocType
from app.recurring.base import CashEffect, RecurringHandler
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate, SalesAmountsInput
from app.schemas.sales_document import SalesDocumentCreate
from app.services.invoice_service import InvoiceService
from app.services.sales_common import calculate_totals
from app.services.sales_document_service import SalesDocumentService


def first_error(error: ValidationError) -> str:
    detail = error.errors()[0]
    field = ".".join(str(part) for part in detail["loc"])
    return f"Template: {field}: {detail['msg']}"


class InvoiceTemplate(SalesAmountsInput):
    customer_id: int
    terms_id: int | None = None
    memo: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


class SalesReceiptTemplate(SalesAmountsInput):
    customer_id: int
    memo: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)
    money_account_id: int | None = None
    payment_method: str | None = None
    reference_no: str | None = None


def form_total(template: InvoiceTemplate | SalesReceiptTemplate) -> Decimal:
    """Lines minus discount plus shipping, before sales tax, in the form's currency."""
    amounts = [SimpleNamespace(amount=to_money(line.quantity * line.rate)) for line in template.lines]
    return calculate_totals(amounts, template.discount_type, template.discount_value, template.shipping_amount).total


class InvoiceRecurringHandler(RecurringHandler):
    transaction_type = RecurringType.INVOICE

    def __init__(self, invoice_service: InvoiceService):
        self.invoice_service = invoice_service

    def check_template(self, company_id: int, template: dict) -> dict:
        try:
            parsed = InvoiceTemplate.model_validate(template)
        except ValidationError as error:
            raise BusinessRuleError(first_error(error))
        return parsed.model_dump(mode="json")

    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        data = dict(template)
        data["invoice_date"] = transaction_date
        invoice = self.invoice_service.create(company_id, InvoiceCreate.model_validate(data))
        return invoice.id

    def cash_effects(self, company_id: int, template: dict, transaction_date: date) -> list[CashEffect]:
        """The customer pays on the due date their terms give."""
        service = self.invoice_service
        data = InvoiceTemplate.model_validate(template)
        company = service.company_repository.get(company_id)
        customer = service.customer_repository.get(company_id, data.customer_id)
        due_date, _ = service.terms_service.due_date_for(company, customer, transaction_date, data.terms_id)
        rate = service.currencies.rate_for(company_id, customer.currency_code, transaction_date, data.exchange_rate)
        return [CashEffect(due_date, to_money(form_total(data) * rate), customer.id, on_terms=True)]


class SalesReceiptRecurringHandler(RecurringHandler):
    transaction_type = RecurringType.SALES_RECEIPT

    def __init__(self, sales_document_service: SalesDocumentService):
        self.sales_document_service = sales_document_service

    def check_template(self, company_id: int, template: dict) -> dict:
        try:
            parsed = SalesReceiptTemplate.model_validate(template)
        except ValidationError as error:
            raise BusinessRuleError(first_error(error))
        return parsed.model_dump(mode="json")

    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        data = dict(template)
        data["doc_type"] = SalesDocType.SALES_RECEIPT
        data["doc_date"] = transaction_date
        receipt = self.sales_document_service.create(company_id, SalesDocumentCreate.model_validate(data))
        return receipt.id

    def cash_effects(self, company_id: int, template: dict, transaction_date: date) -> list[CashEffect]:
        """A sales receipt is paid on the spot."""
        service = self.sales_document_service
        data = SalesReceiptTemplate.model_validate(template)
        customer = service.customer_repository.get(company_id, data.customer_id)
        rate = service.currencies.rate_for(company_id, customer.currency_code, transaction_date, data.exchange_rate)
        return [CashEffect(transaction_date, to_money(form_total(data) * rate), customer.id)]
