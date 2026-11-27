"""
Recurring bills and recurring expenses (e.g. monthly rent).
"""

from datetime import date

from pydantic import Field, ValidationError

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.models.enums import ExpenseKind, PaymentMethod, PurchaseDocType, RecurringType
from app.recurring.base import CashEffect, RecurringHandler
from app.recurring.sales_handlers import first_error
from app.schemas.common import CleanStringsModel
from app.schemas.expense import ExpenseCreate, ExpenseLineCreate
from app.schemas.purchase import PurchaseDocumentCreate, PurchaseLineInput
from app.seed.default_accounts import DetailType
from app.services.expense_service import ExpenseService
from app.services.purchase_document_service import PurchaseDocumentService


class BillTemplate(CleanStringsModel):
    vendor_id: int
    terms_id: int | None = None
    memo: str | None = None
    lines: list[PurchaseLineInput] = Field(min_length=1)


class ExpenseTemplate(CleanStringsModel):
    kind: ExpenseKind = ExpenseKind.EXPENSE
    vendor_id: int | None = None
    payment_account_id: int
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    memo: str | None = None
    lines: list[ExpenseLineCreate] = Field(min_length=1)


class BillRecurringHandler(RecurringHandler):
    transaction_type = RecurringType.BILL

    def __init__(self, purchase_service: PurchaseDocumentService):
        self.purchase_service = purchase_service

    def check_template(self, company_id: int, template: dict) -> dict:
        try:
            return BillTemplate.model_validate(template).model_dump(mode="json")
        except ValidationError as error:
            raise BusinessRuleError(first_error(error))

    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        data = dict(template)
        data["doc_type"] = PurchaseDocType.BILL
        data["doc_date"] = transaction_date
        bill = self.purchase_service.create(company_id, PurchaseDocumentCreate.model_validate(data))
        return bill.id

    def cash_effects(self, company_id: int, template: dict, transaction_date: date) -> list[CashEffect]:
        """A bill is paid on its due date."""
        service = self.purchase_service
        data = PurchaseDocumentCreate.model_validate({**template, "doc_type": PurchaseDocType.BILL, "doc_date": transaction_date})
        vendor = service.vendor_repository.get(company_id, data.vendor_id)
        due_date, _ = service.due_date_for(company_id, vendor, data)
        total = sum((to_money(line.quantity * line.rate) for line in data.lines), ZERO)
        rate = service.currencies.rate_for(company_id, vendor.currency_code, transaction_date)
        return [CashEffect(due_date, -to_money(total * rate))]


class ExpenseRecurringHandler(RecurringHandler):
    transaction_type = RecurringType.EXPENSE

    def __init__(self, expense_service: ExpenseService):
        self.expense_service = expense_service

    def check_template(self, company_id: int, template: dict) -> dict:
        try:
            return ExpenseTemplate.model_validate(template).model_dump(mode="json")
        except ValidationError as error:
            raise BusinessRuleError(first_error(error))

    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        data = dict(template)
        data["expense_date"] = transaction_date
        # Recurring checks are saved as "print later", so they are numbered when printed.
        if data.get("kind") == ExpenseKind.CHECK.value:
            data["print_later"] = True
        expense = self.expense_service.create(company_id, ExpenseCreate.model_validate(data))
        return expense.id

    def cash_effects(self, company_id: int, template: dict, transaction_date: date) -> list[CashEffect]:
        """Paid from a bank account, money leaves the bank right away. Card spending does not."""
        service = self.expense_service
        data = ExpenseTemplate.model_validate(template)
        account = service.account_repository.get(company_id, data.payment_account_id)
        if account is None or account.detail_type != DetailType.BANK:
            return []
        vendor = service.vendor_repository.get(company_id, data.vendor_id) if data.vendor_id else None
        rate = service.currencies.rate_for(company_id, vendor.currency_code if vendor else None, transaction_date)
        total = sum((line.amount for line in data.lines), ZERO)
        return [CashEffect(transaction_date, -to_money(total * rate))]
