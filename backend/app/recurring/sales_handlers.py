"""
Recurring invoices and recurring sales receipts.

A template is the normal create request without its date. When the
schedule runs, the date is filled in and the normal service creates it.
"""

from datetime import date

from pydantic import Field, ValidationError

from app.core.exceptions import BusinessRuleError
from app.models.enums import RecurringType, SalesDocType
from app.recurring.base import RecurringHandler
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate, SalesAmountsInput
from app.schemas.sales_document import SalesDocumentCreate
from app.services.invoice_service import InvoiceService
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
