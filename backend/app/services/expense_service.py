"""
Expenses and checks (money paid out right away).

    Debit  Expense category account(s)   (what the money was spent on)
    Credit Bank or Credit Card account   (where the money came from)

A check is an expense paid from a bank account with a check number.
A credit card credit (a refund onto the card) is the exact opposite:
    Debit  Credit Card account
    Credit Category account(s)
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import Account, Expense, ExpenseLine
from app.models.enums import AccountType, ExpenseKind, JournalSource, PaymentMethod
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.expense import ExpenseCreate
from app.seed.default_accounts import DetailType, SystemAccount
from app.services.base import BaseService
from app.services.check_numbers import CheckNumberService
from app.services.inventory_service import InventoryService, StockSource
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.tracking_service import TrackingService


STOCK_SOURCE = "EXPENSE"


class ExpenseService(BaseService):
    def __init__(
        self,
        session,
        expense_repository: ExpenseRepository,
        vendor_repository: VendorRepository,
        customer_repository: CustomerRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        check_numbers: CheckNumberService,
        ledger: LedgerService,
        inventory: InventoryService,
        tracking: TrackingService,
    ):
        super().__init__(session)
        self.inventory = inventory
        self.tracking = tracking
        self.expense_repository = expense_repository
        self.vendor_repository = vendor_repository
        self.customer_repository = customer_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.check_numbers = check_numbers
        self.ledger = ledger

    def list(self, company_id: int) -> list[Expense]:
        return self.expense_repository.list_all(company_id)

    def get(self, company_id: int, expense_id: int) -> Expense:
        expense = self.expense_repository.get(company_id, expense_id)
        if expense is None:
            raise NotFoundError("Expense not found.")
        return expense

    def create(self, company_id: int, data: ExpenseCreate) -> Expense:
        if data.vendor_id is not None:
            vendor = self.vendor_repository.get(company_id, data.vendor_id)
            if vendor is None:
                raise BusinessRuleError("Please choose an existing vendor.")

        tracking = self.tracking.check(company_id, data)
        is_check = data.kind == ExpenseKind.CHECK
        is_card_credit = data.kind == ExpenseKind.CARD_CREDIT
        payment_account = self.get_payment_account(company_id, data.payment_account_id, is_check)
        if is_card_credit and not (payment_account.account_type == AccountType.LIABILITY and payment_account.detail_type == DetailType.CREDIT_CARD):
            raise BusinessRuleError("A credit card credit must go on a credit card account.")

        expense = Expense(
            company_id=company_id,
            kind=data.kind,
            vendor_id=data.vendor_id,
            payment_account_id=payment_account.id,
            expense_date=data.expense_date,
            payment_method=self.method_for(data),
            reference_no=data.reference_no,
            print_later=is_check and data.print_later,
            memo=data.memo,
        )
        if is_check and not data.print_later:
            expense.check_number = self.check_numbers.assign(company_id, payment_account.id, data.check_number)

        total = ZERO
        ledger_lines = []
        for line_data in data.lines:
            account_id, product = self.inventory.purchase_line_account(company_id, line_data.product_id, line_data.account_id)
            category = self.account_repository.get(company_id, account_id)
            if category is None or not category.is_active:
                raise BusinessRuleError("Please choose an active category for every line.")
            if category.id == payment_account.id:
                raise BusinessRuleError("A category cannot be the same account the money was paid from.")
            if line_data.customer_id is not None and self.customer_repository.get(company_id, line_data.customer_id) is None:
                raise BusinessRuleError("The billable customer does not exist.")

            description = line_data.description
            if description is None and product is not None:
                description = product.purchase_description or product.name
            expense.lines.append(
                ExpenseLine(
                    account_id=category.id,
                    product_id=product.id if product else None,
                    quantity=line_data.quantity,
                    description=description,
                    amount=line_data.amount,
                    customer_id=line_data.customer_id,
                )
            )
            if is_card_credit:
                ledger_lines.append(LedgerLine(category.id, credit=line_data.amount, description=description))
            else:
                ledger_lines.append(LedgerLine(category.id, debit=line_data.amount, description=description))
            total += line_data.amount

        expense.total = total
        if is_card_credit:
            ledger_lines.append(LedgerLine(payment_account.id, debit=total))
        else:
            ledger_lines.append(LedgerLine(payment_account.id, credit=total))
        self.tracking.apply(expense, tracking)
        self.expense_repository.add(expense)
        stock = StockSource(STOCK_SOURCE, expense.id, expense.expense_date, expense.memo or "Expense")
        ledger_lines.extend(self.inventory.purchase_lines(company_id, expense.lines, stock, is_return=is_card_credit))

        entry = self.ledger.post(
            company_id=company_id,
            entry_date=expense.expense_date,
            source_type=self.journal_source_for(data.kind),
            source_id=expense.id,
            memo=expense.memo or data.kind.value.replace("_", " ").title(),
            lines=ledger_lines,
            tracking=tracking,
        )
        expense.journal_entry_id = entry.id

        self.commit()
        return expense

    def method_for(self, data: ExpenseCreate) -> PaymentMethod:
        if data.kind == ExpenseKind.CHECK:
            return PaymentMethod.CHECK
        if data.kind == ExpenseKind.CARD_CREDIT:
            return PaymentMethod.CREDIT_CARD
        return data.payment_method

    def journal_source_for(self, kind: ExpenseKind) -> JournalSource:
        if kind == ExpenseKind.CHECK:
            return JournalSource.CHECK
        if kind == ExpenseKind.CARD_CREDIT:
            return JournalSource.CARD_CREDIT
        return JournalSource.EXPENSE

    def get_payment_account(self, company_id: int, account_id: int, is_check: bool) -> Account:
        """Expenses are paid from a bank (asset) or credit card (liability). Checks only from a bank."""
        account = self.account_repository.get(company_id, account_id)
        allowed_types = (AccountType.ASSET,) if is_check else (AccountType.ASSET, AccountType.LIABILITY)
        if account is None or not account.is_active or account.account_type not in allowed_types:
            if is_check:
                raise BusinessRuleError("Checks must be written from a bank account.")
            raise BusinessRuleError("Please choose a bank or credit card account to pay from.")
        if account.system_key in (SystemAccount.ACCOUNTS_RECEIVABLE, SystemAccount.ACCOUNTS_PAYABLE):
            raise BusinessRuleError("Please choose a bank or credit card account to pay from.")
        return account

    def void(self, company_id: int, expense_id: int) -> Expense:
        expense = self.get(company_id, expense_id)
        if expense.is_void:
            raise BusinessRuleError("This expense is already void.")
        original = self.journal_repository.get(company_id, expense.journal_entry_id)
        self.ledger.reverse(company_id, original, date.today(), JournalSource.EXPENSE_VOID, "Void")
        self.inventory.undo(company_id, STOCK_SOURCE, expense.id, date.today(), "Void of expense")
        expense.is_void = True
        expense.print_later = False
        self.commit()
        return expense
