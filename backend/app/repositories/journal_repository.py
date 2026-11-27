from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Account, JournalEntry, JournalLine
from app.repositories.base import BaseRepository
from app.seed.default_accounts import DetailType


class AccountTotals:
    """Sum of debits and credits for one account over a period."""

    def __init__(self, account: Account, debit: Decimal, credit: Decimal):
        self.account = account
        self.debit = debit
        self.credit = credit

    @property
    def balance(self) -> Decimal:
        """Balance shown the "natural" way for the account type (always positive when normal)."""
        if self.account.account_type.increases_with_debit():
            return self.debit - self.credit
        return self.credit - self.debit


class JournalRepository(BaseRepository):
    model = JournalEntry

    def order_by_columns(self) -> list:
        return [JournalEntry.entry_date.desc(), JournalEntry.id.desc()]

    def list_for_source(self, company_id: int, source_type, source_id: int) -> list[JournalEntry]:
        query = select(JournalEntry).where(
            JournalEntry.company_id == company_id,
            JournalEntry.source_type == source_type,
            JournalEntry.source_id == source_id,
        )
        return list(self.session.scalars(query))

    def bank_totals(self, company_id: int, as_of: date) -> list[AccountTotals]:
        """The balance of every bank account on a day."""
        return [totals for totals in self.totals_by_account(company_id, None, as_of) if totals.account.detail_type == DetailType.BANK]

    def totals_by_account(self, company_id: int, start_date: date | None, end_date: date) -> list[AccountTotals]:
        """
        Add up every journal line per account between two dates.
        When start_date is None, everything up to end_date is included
        (that is what the Balance Sheet needs).
        """
        debit_sum = func.coalesce(func.sum(JournalLine.debit), 0)
        credit_sum = func.coalesce(func.sum(JournalLine.credit), 0)

        query = (
            select(Account, debit_sum, credit_sum)
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.entry_date <= end_date,
            )
            .group_by(Account.id)
            .order_by(Account.code, Account.name)
        )
        if start_date is not None:
            query = query.where(JournalEntry.entry_date >= start_date)

        results = []
        for account, debit, credit in self.session.execute(query):
            results.append(AccountTotals(account, Decimal(debit), Decimal(credit)))
        return results
