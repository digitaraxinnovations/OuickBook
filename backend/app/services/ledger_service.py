"""
The heart of the accounting system: posting double-entry journal entries.

Every other service (invoices, payments, expenses, manual journals) posts
through this one class, so the "debits must equal credits" rule lives in
exactly one place.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.models import JournalEntry, JournalLine
from app.models.enums import JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.journal_repository import JournalRepository


class LedgerLine:
    """One debit or credit to be posted. A plain value object."""

    def __init__(self, account_id: int, debit=ZERO, credit=ZERO, description: str | None = None):
        self.account_id = account_id
        self.debit = to_money(debit)
        self.credit = to_money(credit)
        self.description = description


class LedgerService:
    def __init__(self, journal_repository: JournalRepository, account_repository: AccountRepository):
        self.journal_repository = journal_repository
        self.account_repository = account_repository

    def post(
        self,
        company_id: int,
        entry_date: date,
        source_type: JournalSource,
        lines: list[LedgerLine],
        memo: str | None = None,
        source_id: int | None = None,
    ) -> JournalEntry:
        """Check the lines and save them as one journal entry. Does not commit."""
        self.check_lines(company_id, lines)

        entry = JournalEntry(
            company_id=company_id,
            entry_date=entry_date,
            memo=memo,
            source_type=source_type,
            source_id=source_id,
        )
        for line in lines:
            entry.lines.append(
                JournalLine(
                    account_id=line.account_id,
                    description=line.description,
                    debit=line.debit,
                    credit=line.credit,
                )
            )
        return self.journal_repository.add(entry)

    def reverse(
        self,
        company_id: int,
        original: JournalEntry,
        entry_date: date,
        source_type: JournalSource,
        memo: str | None = None,
    ) -> JournalEntry:
        """Post a new entry that cancels the original (debits and credits swapped)."""
        reversed_lines = []
        for line in original.lines:
            reversed_lines.append(
                LedgerLine(
                    account_id=line.account_id,
                    debit=line.credit,
                    credit=line.debit,
                    description=line.description,
                )
            )
        entry = self.post(company_id, entry_date, source_type, reversed_lines, memo, original.source_id)
        entry.reverses_entry_id = original.id
        return entry

    def check_lines(self, company_id: int, lines: list[LedgerLine]) -> None:
        if len(lines) < 2:
            raise BusinessRuleError("A journal entry needs at least two lines.")

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for line in lines:
            if line.debit < 0 or line.credit < 0:
                raise BusinessRuleError("Debit and credit amounts cannot be negative.")
            if line.debit > 0 and line.credit > 0:
                raise BusinessRuleError("A line can have a debit or a credit, not both.")
            if line.debit == 0 and line.credit == 0:
                raise BusinessRuleError("Every line needs a debit or a credit amount.")

            account = self.account_repository.get(company_id, line.account_id)
            if account is None:
                raise BusinessRuleError(f"Account {line.account_id} does not exist.")

            total_debit += line.debit
            total_credit += line.credit

        if total_debit != total_credit:
            raise BusinessRuleError(
                f"Debits ({total_debit}) and credits ({total_credit}) must be equal."
            )
