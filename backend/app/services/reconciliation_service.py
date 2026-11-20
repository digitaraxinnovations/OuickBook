"""
Reconciling a bank or credit card account against its statement.

1. Start: enter the statement date and ending balance.
2. Tick every transaction that appears on the statement.
3. When beginning balance + ticked items = statement ending balance
   (difference 0), finish. The ticked lines are marked reconciled.

Amounts are shown the way the statement shows them: for a bank, deposits
are positive; for a credit card, charges are positive (the balance owed).
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import Account, JournalLine, Reconciliation
from app.models.enums import AccountType, ReconciliationStatus
from app.repositories.banking_repositories import ReconciliationRepository, RegisterQueries
from app.schemas.banking import (
    DiscrepancyItem,
    ReconcileItem,
    ReconciliationReport,
    ReconciliationStart,
    ReconciliationWorkspace,
)
from app.services.bank_review_service import BankReviewService
from app.services.base import BaseService


def statement_amount(account: Account, line: JournalLine) -> Decimal:
    if account.account_type == AccountType.LIABILITY:
        return line.credit - line.debit
    return line.debit - line.credit


class ReconciliationService(BaseService):
    def __init__(
        self,
        session,
        repository: ReconciliationRepository,
        register: RegisterQueries,
        review_service: BankReviewService,
    ):
        super().__init__(session)
        self.repository = repository
        self.register = register
        self.review_service = review_service

    # ---------- reading ----------

    def history(self, company_id: int, account_id: int) -> list[Reconciliation]:
        return self.repository.list_for_account(company_id, account_id)

    def get(self, company_id: int, reconciliation_id: int) -> Reconciliation:
        reconciliation = self.repository.get(company_id, reconciliation_id)
        if reconciliation is None:
            raise NotFoundError("Reconciliation not found.")
        return reconciliation

    def last_reconciled_dates(self, company_id: int) -> dict:
        return self.repository.last_reconciled_dates(company_id)

    # ---------- doing it ----------

    def start(self, company_id: int, data: ReconciliationStart) -> Reconciliation:
        """Start (or continue) reconciling an account."""
        account = self.review_service.check_banking_account(company_id, data.account_id)
        existing = self.repository.in_progress(company_id, account.id)
        if existing is not None:
            existing.statement_date = data.statement_date
            existing.ending_balance = data.ending_balance
            self.commit()
            return existing

        last = self.repository.last_completed(company_id, account.id)
        if last is not None and data.statement_date <= last.statement_date:
            raise BusinessRuleError(f"This account is already reconciled up to {last.statement_date}. Choose a later statement date.")

        # Lines the bank already confirmed (matched or added from the bank) start ticked.
        selected = []
        for line in self.register.lines_for_account(company_id, account.id, data.statement_date, unreconciled_only=True):
            if line.cleared:
                selected.append(line.id)

        reconciliation = Reconciliation(
            company_id=company_id,
            account_id=account.id,
            statement_date=data.statement_date,
            beginning_balance=last.ending_balance if last else ZERO,
            ending_balance=data.ending_balance,
            status=ReconciliationStatus.IN_PROGRESS,
            selected_line_ids=selected,
        )
        self.repository.add(reconciliation)
        self.commit()
        return reconciliation

    def workspace(self, company_id: int, reconciliation_id: int) -> ReconciliationWorkspace:
        reconciliation = self.get(company_id, reconciliation_id)
        if reconciliation.status != ReconciliationStatus.IN_PROGRESS:
            raise BusinessRuleError("This reconciliation is finished. Open its report instead.")
        items = self.items_for(company_id, reconciliation)
        cleared = self.cleared_balance(reconciliation, items)
        return ReconciliationWorkspace(
            reconciliation=reconciliation,
            items=items,
            cleared_balance=cleared,
            difference=reconciliation.ending_balance - cleared,
        )

    def select(self, company_id: int, reconciliation_id: int, line_ids: list[int]) -> ReconciliationWorkspace:
        reconciliation = self.get(company_id, reconciliation_id)
        allowed = set()
        for item in self.items_for(company_id, reconciliation):
            allowed.add(item.journal_line_id)
        chosen = []
        for line_id in line_ids:
            if line_id not in allowed:
                raise BusinessRuleError("One of the ticked transactions does not belong to this reconciliation.")
            chosen.append(line_id)
        reconciliation.selected_line_ids = chosen
        self.commit()
        return self.workspace(company_id, reconciliation_id)

    def finish(self, company_id: int, reconciliation_id: int) -> Reconciliation:
        workspace = self.workspace(company_id, reconciliation_id)
        if workspace.difference != 0:
            raise BusinessRuleError(f"The difference must be 0.00 to finish (it is {workspace.difference}).")

        reconciliation = self.get(company_id, reconciliation_id)
        for line_id in reconciliation.selected_line_ids:
            line = self.session.get(JournalLine, line_id)
            line.reconciliation_id = reconciliation.id
            line.cleared = True
        reconciliation.status = ReconciliationStatus.COMPLETED
        reconciliation.completed_at = datetime.now(timezone.utc)
        self.commit()
        return reconciliation

    def undo(self, company_id: int, reconciliation_id: int) -> Reconciliation:
        """Only the latest completed reconciliation of an account can be undone."""
        reconciliation = self.get(company_id, reconciliation_id)
        if reconciliation.status != ReconciliationStatus.COMPLETED:
            raise BusinessRuleError("Only a completed reconciliation can be undone.")
        last = self.repository.last_completed(company_id, reconciliation.account_id)
        if last.id != reconciliation.id:
            raise BusinessRuleError("Undo the most recent reconciliation of this account first.")

        for line in self.register.lines_in_reconciliation(reconciliation.id):
            line.reconciliation_id = None
        reconciliation.status = ReconciliationStatus.UNDONE
        self.commit()
        return reconciliation

    def cancel(self, company_id: int, reconciliation_id: int) -> None:
        reconciliation = self.get(company_id, reconciliation_id)
        if reconciliation.status != ReconciliationStatus.IN_PROGRESS:
            raise BusinessRuleError("Only an unfinished reconciliation can be cancelled.")
        self.session.delete(reconciliation)
        self.commit()

    # ---------- reports ----------

    def report(self, company_id: int, reconciliation_id: int) -> ReconciliationReport:
        reconciliation = self.get(company_id, reconciliation_id)
        account = reconciliation.account

        increases = []
        decreases = []
        for line in self.register.lines_in_reconciliation(reconciliation.id):
            item = self.to_item(account, line, True)
            if item.amount >= 0:
                increases.append(item)
            else:
                decreases.append(item)

        uncleared = []
        register_balance = ZERO
        for line in self.register.lines_for_account(company_id, account.id, reconciliation.statement_date):
            register_balance += statement_amount(account, line)
            if line.reconciliation_id is None:
                uncleared.append(self.to_item(account, line, False))

        increases.sort(key=lambda item: item.entry_date)
        decreases.sort(key=lambda item: item.entry_date)

        cleared = reconciliation.beginning_balance
        for item in increases + decreases:
            cleared += item.amount

        return ReconciliationReport(
            reconciliation=reconciliation,
            cleared_increases=increases,
            cleared_decreases=decreases,
            cleared_balance=cleared,
            uncleared=uncleared,
            register_balance=register_balance,
        )

    def discrepancies(self, company_id: int, account_id: int) -> list[DiscrepancyItem]:
        """Reconciled transactions that were voided or deleted after their reconciliation."""
        account = self.review_service.check_banking_account(company_id, account_id)
        items = []
        for reconciliation in self.repository.list_for_account(company_id, account.id):
            if reconciliation.status != ReconciliationStatus.COMPLETED:
                continue
            lines = self.register.lines_in_reconciliation(reconciliation.id)
            lines_by_entry = {}
            for line in lines:
                lines_by_entry[line.journal_entry_id] = line
            reversals = self.register.reversals_created_after(company_id, list(lines_by_entry.keys()), reconciliation.completed_at)
            for reversal in reversals:
                line = lines_by_entry[reversal.reverses_entry_id]
                items.append(
                    DiscrepancyItem(
                        reconciliation_id=reconciliation.id,
                        statement_date=reconciliation.statement_date,
                        entry_date=line.entry.entry_date,
                        description=line.entry.memo or line.entry.source_type.value,
                        amount=statement_amount(account, line),
                        changed_on=reversal.entry_date,
                        change="Voided or deleted after it was reconciled",
                    )
                )
        return items

    # ---------- helpers ----------

    def items_for(self, company_id: int, reconciliation: Reconciliation) -> list[ReconcileItem]:
        account = reconciliation.account
        selected = set(reconciliation.selected_line_ids or [])
        items = []
        for line in self.register.lines_for_account(company_id, account.id, reconciliation.statement_date, unreconciled_only=True):
            items.append(self.to_item(account, line, line.id in selected))
        return items

    def to_item(self, account: Account, line: JournalLine, selected: bool) -> ReconcileItem:
        entry = line.entry
        return ReconcileItem(
            journal_line_id=line.id,
            entry_date=entry.entry_date,
            transaction_type=entry.source_type.value.replace("_", " ").title(),
            description=entry.memo or line.description or "",
            amount=statement_amount(account, line),
            selected=selected,
        )

    def cleared_balance(self, reconciliation: Reconciliation, items: list[ReconcileItem]) -> Decimal:
        balance = reconciliation.beginning_balance
        for item in items:
            if item.selected:
                balance += item.amount
        return balance
