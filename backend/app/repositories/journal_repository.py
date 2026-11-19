from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Account, JournalEntry, JournalLine
from app.repositories.base import BaseRepository


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
