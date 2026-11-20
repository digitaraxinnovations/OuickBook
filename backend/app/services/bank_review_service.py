"""
The banking "For review" queue.

Every imported bank line is reviewed once, in one of three ways:
- Match:    it is already in the books (e.g. a payment you recorded) - link them.
- Add:      create the transaction from it (expense, deposit, transfer or card credit).
            Several category lines = a split.
- Exclude:  a duplicate or personal item - ignore it.

Whatever is created is a normal transaction made by the normal services,
so the ledger rules are the same as everywhere else.
"""

from datetime import timedelta

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import Account, BankTransaction, JournalLine
from app.models.enums import AccountType, BankTransactionStatus, ExpenseKind, PaymentMethod
from app.repositories.account_repository import AccountRepository
from app.repositories.banking_repositories import BankTransactionRepository, RegisterQueries
from app.repositories.journal_repository import JournalRepository
from app.schemas.banking import AddLineInput, AddTransactionRequest, BankAccountOverview, MatchCandidate, TransferCreate
from app.schemas.expense import ExpenseCreate, ExpenseLineCreate
from app.schemas.sales_extras import DepositCreate, DepositOtherLineInput
from app.seed.default_accounts import DetailType
from app.services.base import BaseService
from app.services.deposit_service import DepositService
from app.services.expense_service import ExpenseService
from app.services.transfer_service import TransferService

BANKING_DETAIL_TYPES = (DetailType.BANK, DetailType.CREDIT_CARD)


def line_signed_amount(line: JournalLine) -> object:
    """Money into the account is positive (a debit), money out is negative - same as bank lines."""
    return line.debit - line.credit


def is_banking_account(account: Account | None) -> bool:
    return account is not None and account.detail_type in BANKING_DETAIL_TYPES


class BankReviewService(BaseService):
    def __init__(
        self,
        session,
        repository: BankTransactionRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        register: RegisterQueries,
        expense_service: ExpenseService,
        deposit_service: DepositService,
        transfer_service: TransferService,
        match_days: int,
    ):
        super().__init__(session)
        self.repository = repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.register = register
        self.expense_service = expense_service
        self.deposit_service = deposit_service
        self.transfer_service = transfer_service
        self.match_days = match_days

    # ---------- reading ----------

    def list(self, company_id: int, account_id: int | None, status: BankTransactionStatus | None) -> list[BankTransaction]:
        return self.repository.list_for(company_id, account_id, status)

    def get(self, company_id: int, transaction_id: int) -> BankTransaction:
        transaction = self.repository.get(company_id, transaction_id)
        if transaction is None:
            raise NotFoundError("Bank transaction not found.")
        return transaction

    def banking_accounts(self, company_id: int) -> list[Account]:
        accounts = []
        for account in self.account_repository.list_all(company_id, active_only=True):
            if is_banking_account(account):
                accounts.append(account)
        return accounts

    def check_banking_account(self, company_id: int, account_id: int) -> Account:
        account = self.account_repository.get(company_id, account_id)
        if not is_banking_account(account):
            raise BusinessRuleError("Choose a bank or credit card account.")
        return account

    # ---------- matching ----------

    def find_matches(self, company_id: int, transaction_id: int) -> list[MatchCandidate]:
        """Book transactions on the same account, same amount, close in date, not yet linked."""
        transaction = self.get(company_id, transaction_id)
        linked = self.repository.linked_line_ids(company_id)
        earliest = transaction.txn_date - timedelta(days=self.match_days)
        latest = transaction.txn_date + timedelta(days=self.match_days)

        candidates = []
        for line in self.register.lines_for_account(company_id, transaction.account_id, up_to=latest):
            entry = line.entry
            if line.id in linked or entry.entry_date < earliest:
                continue
            if line_signed_amount(line) != transaction.amount:
                continue
            candidates.append(
                MatchCandidate(
                    journal_line_id=line.id,
                    entry_date=entry.entry_date,
                    description=entry.memo or entry.source_type.value.replace("_", " ").title(),
                    amount=line_signed_amount(line),
                )
            )
        candidates.sort(key=lambda candidate: abs((candidate.entry_date - transaction.txn_date).days))
        return candidates

    def match(self, company_id: int, transaction_id: int, journal_line_id: int) -> BankTransaction:
        transaction = self.get_for_review(company_id, transaction_id)
        valid_ids = []
        for candidate in self.find_matches(company_id, transaction_id):
            valid_ids.append(candidate.journal_line_id)
        if journal_line_id not in valid_ids:
            raise BusinessRuleError("That transaction cannot be matched (different account, amount or date, or already matched).")

        line = self.session.get(JournalLine, journal_line_id)
        line.cleared = True
        transaction.status = BankTransactionStatus.MATCHED
        transaction.journal_line_id = line.id
        transaction.added_as = "MATCH"
        self.commit()
        return transaction

    # ---------- adding ----------

    def add(self, company_id: int, transaction_id: int, data: AddTransactionRequest) -> BankTransaction:
        transaction = self.get_for_review(company_id, transaction_id)
        account = transaction.account

        total = ZERO
        for line in data.lines:
            total += line.amount
        if total != abs(transaction.amount):
            raise BusinessRuleError(f"The split lines add up to {total}, but the bank amount is {abs(transaction.amount)}.")

        money_in = transaction.amount > 0
        is_card = account.account_type == AccountType.LIABILITY
        memo = data.memo or transaction.description
        vendor_id = data.vendor_id or transaction.suggested_vendor_id
        first_account = self.account_repository.get(company_id, data.lines[0].account_id)

        if len(data.lines) == 1 and is_banking_account(first_account):
            created_as, created_id, entry_id = self.add_transfer(company_id, transaction, first_account, money_in, memo)
        elif not money_in:
            created_as, created_id, entry_id = self.add_expense(company_id, transaction, data.lines, vendor_id, memo, ExpenseKind.EXPENSE, is_card)
        elif is_card:
            created_as, created_id, entry_id = self.add_expense(company_id, transaction, data.lines, vendor_id, memo, ExpenseKind.CARD_CREDIT, True)
        else:
            created_as, created_id, entry_id = self.add_deposit(company_id, transaction, data.lines, memo)

        line = self.line_on_account(company_id, entry_id, account.id)
        line.cleared = True
        transaction.status = BankTransactionStatus.ADDED
        transaction.journal_line_id = line.id
        transaction.added_as = created_as
        transaction.added_id = created_id
        self.commit()
        return transaction

    def add_transfer(self, company_id: int, transaction: BankTransaction, other: Account, money_in: bool, memo: str):
        if other.id == transaction.account_id:
            raise BusinessRuleError("A transfer needs a different account.")
        if money_in:
            from_id, to_id = other.id, transaction.account_id
        else:
            from_id, to_id = transaction.account_id, other.id
        transfer = self.transfer_service.create(
            company_id,
            TransferCreate(transfer_date=transaction.txn_date, from_account_id=from_id, to_account_id=to_id, amount=abs(transaction.amount), memo=memo),
        )
        return "TRANSFER", transfer.id, transfer.journal_entry_id

    def add_expense(self, company_id, transaction, lines: list[AddLineInput], vendor_id, memo, kind: ExpenseKind, is_card: bool):
        expense_lines = []
        for line in lines:
            expense_lines.append(ExpenseLineCreate(account_id=line.account_id, amount=line.amount, description=line.description))
        expense = self.expense_service.create(
            company_id,
            ExpenseCreate(
                kind=kind,
                vendor_id=vendor_id,
                payment_account_id=transaction.account_id,
                expense_date=transaction.txn_date,
                payment_method=PaymentMethod.CREDIT_CARD if is_card else PaymentMethod.BANK_TRANSFER,
                memo=memo,
                lines=expense_lines,
            ),
        )
        label = "CARD_CREDIT" if kind == ExpenseKind.CARD_CREDIT else "EXPENSE"
        return label, expense.id, expense.journal_entry_id

    def add_deposit(self, company_id, transaction, lines: list[AddLineInput], memo):
        other_lines = []
        for line in lines:
            other_lines.append(DepositOtherLineInput(account_id=line.account_id, amount=line.amount, description=line.description))
        deposit = self.deposit_service.create(
            company_id,
            DepositCreate(deposit_date=transaction.txn_date, bank_account_id=transaction.account_id, memo=memo, other_lines=other_lines),
        )
        return "DEPOSIT", deposit.id, deposit.journal_entry_id

    def line_on_account(self, company_id: int, entry_id: int, account_id: int) -> JournalLine:
        entry = self.journal_repository.get(company_id, entry_id)
        for line in entry.lines:
            if line.account_id == account_id:
                return line
        raise BusinessRuleError("The new transaction does not touch this account.")

    # ---------- exclude / undo ----------

    def exclude(self, company_id: int, transaction_id: int) -> BankTransaction:
        transaction = self.get_for_review(company_id, transaction_id)
        transaction.status = BankTransactionStatus.EXCLUDED
        self.commit()
        return transaction

    def undo(self, company_id: int, transaction_id: int) -> BankTransaction:
        """Send a reviewed line back to "For review". Added transactions are voided."""
        transaction = self.get(company_id, transaction_id)
        if transaction.status == BankTransactionStatus.FOR_REVIEW:
            raise BusinessRuleError("This line is still waiting for review.")

        line = None
        if transaction.journal_line_id is not None:
            line = self.session.get(JournalLine, transaction.journal_line_id)
            if line.reconciliation_id is not None:
                raise BusinessRuleError("This transaction is reconciled. Undo the reconciliation first.")

        if transaction.status == BankTransactionStatus.ADDED:
            if transaction.added_as in ("EXPENSE", "CARD_CREDIT"):
                self.expense_service.void(company_id, transaction.added_id)
            elif transaction.added_as == "TRANSFER":
                self.transfer_service.void(company_id, transaction.added_id)
            else:
                raise BusinessRuleError("Deposits created from the bank cannot be undone here yet. Add a journal entry to correct it.")
        elif line is not None:
            line.cleared = False

        transaction.status = BankTransactionStatus.FOR_REVIEW
        transaction.journal_line_id = None
        transaction.added_as = None
        transaction.added_id = None
        self.commit()
        return transaction

    def get_for_review(self, company_id: int, transaction_id: int) -> BankTransaction:
        transaction = self.get(company_id, transaction_id)
        if transaction.status != BankTransactionStatus.FOR_REVIEW:
            raise BusinessRuleError("This bank line has already been reviewed.")
        return transaction

    # ---------- overview ----------

    def overview(self, company_id: int, last_reconciled: dict) -> list[BankAccountOverview]:
        counts = self.repository.review_counts(company_id)
        imported = self.repository.last_imported(company_id)
        result = []
        for account in self.banking_accounts(company_id):
            balance = ZERO
            for line in self.register.lines_for_account(company_id, account.id):
                balance += line_signed_amount(line)
            if account.account_type == AccountType.LIABILITY:
                balance = -balance  # show what you owe on the card as a positive number
            result.append(
                BankAccountOverview(
                    account=account,
                    detail_type=account.detail_type,
                    books_balance=balance,
                    for_review_count=counts.get(account.id, 0),
                    last_imported=imported.get(account.id),
                    last_reconciled=last_reconciled.get(account.id),
                )
            )
        return result
