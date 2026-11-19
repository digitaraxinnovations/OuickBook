"""
Expenses (money paid out right away).

    Debit  Expense category account(s)   (what the money was spent on)
    Credit Bank or Credit Card account   (where the money came from)
"""

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import Account, Expense, ExpenseLine
from app.models.enums import AccountType, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import VendorRepository
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService


class ExpenseService(BaseService):
    def __init__(
        self,
        session,
        expense_repository: ExpenseRepository,
        vendor_repository: VendorRepository,
        account_repository: AccountRepository,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.expense_repository = expense_repository
        self.vendor_repository = vendor_repository
        self.account_repository = account_repository
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

        payment_account = self.get_payment_account(company_id, data.payment_account_id)

        expense = Expense(
            company_id=company_id,
            vendor_id=data.vendor_id,
            payment_account_id=payment_account.id,
            expense_date=data.expense_date,
            payment_method=data.payment_method,
            reference_no=data.reference_no,
            memo=data.memo,
        )

        total = ZERO
        ledger_lines = []
        for line_data in data.lines:
            category = self.account_repository.get(company_id, line_data.account_id)
            if category is None or not category.is_active:
                raise BusinessRuleError("Please choose an active category for every line.")
            if category.id == payment_account.id:
                raise BusinessRuleError("A category cannot be the same account the money was paid from.")

            expense.lines.append(
                ExpenseLine(account_id=category.id, description=line_data.description, amount=line_data.amount)
            )
            ledger_lines.append(LedgerLine(category.id, debit=line_data.amount, description=line_data.description))
            total += line_data.amount

        expense.total = total
        ledger_lines.append(LedgerLine(payment_account.id, credit=total))
        self.expense_repository.add(expense)

        entry = self.ledger.post(
            company_id=company_id,
            entry_date=expense.expense_date,
            source_type=JournalSource.EXPENSE,
            source_id=expense.id,
            memo=expense.memo or "Expense",
            lines=ledger_lines,
        )
        expense.journal_entry_id = entry.id

        self.commit()
        return expense

    def get_payment_account(self, company_id: int, account_id: int) -> Account:
        """Expenses are paid from a bank (asset) or credit card (liability) account."""
        account = self.account_repository.get(company_id, account_id)
        allowed_types = (AccountType.ASSET, AccountType.LIABILITY)
        if account is None or not account.is_active or account.account_type not in allowed_types:
            raise BusinessRuleError("Please choose a bank or credit card account to pay from.")
        return account
