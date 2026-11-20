from datetime import date, datetime

from sqlalchemy import func, select

from app.models import BankRule, BankTransaction, JournalEntry, JournalLine, Reconciliation, Transfer
from app.models.enums import BankTransactionStatus, ReconciliationStatus
from app.repositories.base import BaseRepository


class TransferRepository(BaseRepository):
    model = Transfer

    def order_by_columns(self) -> list:
        return [Transfer.transfer_date.desc(), Transfer.id.desc()]


class BankTransactionRepository(BaseRepository):
    model = BankTransaction

    def order_by_columns(self) -> list:
        return [BankTransaction.txn_date.desc(), BankTransaction.id.desc()]

    def list_for(self, company_id: int, account_id: int | None, status: BankTransactionStatus | None) -> list[BankTransaction]:
        query = select(BankTransaction).where(BankTransaction.company_id == company_id)
        if account_id is not None:
            query = query.where(BankTransaction.account_id == account_id)
        if status is not None:
            query = query.where(BankTransaction.status == status)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def existing_external_ids(self, company_id: int, account_id: int) -> set[str]:
        query = select(BankTransaction.external_id).where(
            BankTransaction.company_id == company_id, BankTransaction.account_id == account_id
        )
        return set(self.session.scalars(query))

    def linked_line_ids(self, company_id: int) -> set[int]:
        """Journal lines already matched to or created from a bank line."""
        query = select(BankTransaction.journal_line_id).where(
            BankTransaction.company_id == company_id, BankTransaction.journal_line_id.is_not(None)
        )
        return set(self.session.scalars(query))

    def review_counts(self, company_id: int) -> dict[int, int]:
        query = (
            select(BankTransaction.account_id, func.count(BankTransaction.id))
            .where(BankTransaction.company_id == company_id, BankTransaction.status == BankTransactionStatus.FOR_REVIEW)
            .group_by(BankTransaction.account_id)
        )
        result = {}
        for account_id, count in self.session.execute(query):
            result[account_id] = count
        return result

    def last_imported(self, company_id: int) -> dict[int, date]:
        query = (
            select(BankTransaction.account_id, func.max(BankTransaction.txn_date))
            .where(BankTransaction.company_id == company_id)
            .group_by(BankTransaction.account_id)
        )
        result = {}
        for account_id, last in self.session.execute(query):
            result[account_id] = last
        return result


class BankRuleRepository(BaseRepository):
    model = BankRule

    def order_by_columns(self) -> list:
        return [BankRule.priority, BankRule.id]


class ReconciliationRepository(BaseRepository):
    model = Reconciliation

    def order_by_columns(self) -> list:
        return [Reconciliation.statement_date.desc(), Reconciliation.id.desc()]

    def list_for_account(self, company_id: int, account_id: int) -> list[Reconciliation]:
        query = select(Reconciliation).where(Reconciliation.company_id == company_id, Reconciliation.account_id == account_id)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def in_progress(self, company_id: int, account_id: int) -> Reconciliation | None:
        query = select(Reconciliation).where(
            Reconciliation.company_id == company_id,
            Reconciliation.account_id == account_id,
            Reconciliation.status == ReconciliationStatus.IN_PROGRESS,
        )
        return self.session.scalar(query)

    def last_completed(self, company_id: int, account_id: int) -> Reconciliation | None:
        query = (
            select(Reconciliation)
            .where(
                Reconciliation.company_id == company_id,
                Reconciliation.account_id == account_id,
                Reconciliation.status == ReconciliationStatus.COMPLETED,
            )
            .order_by(Reconciliation.statement_date.desc(), Reconciliation.id.desc())
        )
        return self.session.scalars(query).first()

    def last_reconciled_dates(self, company_id: int) -> dict[int, date]:
        query = (
            select(Reconciliation.account_id, func.max(Reconciliation.statement_date))
            .where(Reconciliation.company_id == company_id, Reconciliation.status == ReconciliationStatus.COMPLETED)
            .group_by(Reconciliation.account_id)
        )
        result = {}
        for account_id, last in self.session.execute(query):
            result[account_id] = last
        return result


class RegisterQueries:
    """Journal lines of one bank or card account (its "register")."""

    def __init__(self, session):
        self.session = session

    def lines_for_account(
        self,
        company_id: int,
        account_id: int,
        up_to: date | None = None,
        unreconciled_only: bool = False,
    ) -> list[JournalLine]:
        query = (
            select(JournalLine)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalLine.account_id == account_id)
        )
        if up_to is not None:
            query = query.where(JournalEntry.entry_date <= up_to)
        if unreconciled_only:
            query = query.where(JournalLine.reconciliation_id.is_(None))
        return list(self.session.scalars(query.order_by(JournalEntry.entry_date, JournalLine.id)))

    def lines_in_reconciliation(self, reconciliation_id: int) -> list[JournalLine]:
        query = select(JournalLine).where(JournalLine.reconciliation_id == reconciliation_id)
        return list(self.session.scalars(query))

    def reversals_created_after(self, company_id: int, entry_ids: list[int], after: datetime) -> list[JournalEntry]:
        if not entry_ids:
            return []
        query = select(JournalEntry).where(
            JournalEntry.company_id == company_id,
            JournalEntry.reverses_entry_id.in_(entry_ids),
            JournalEntry.created_at > after,
        )
        return list(self.session.scalars(query))
