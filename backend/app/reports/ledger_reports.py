"""
Detail reports built from journal lines:

- General Ledger:        every account, its starting balance, each transaction and the running balance.
- Account QuickReport:   the same for one account (choose it with the account filter).
- Balance Sheet Detail:  the General Ledger for balance sheet accounts only.
- Journal:               every journal entry with its debits and credits.
- Transaction List by Date: one line per transaction.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.money import ZERO
from app.models import Account, JournalEntry, JournalLine
from app.models.enums import AccountType
from app.reports.base import Report
from app.reports.report_data import SourceNames
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow

DETAIL_COLUMNS = ["Date", "Type", "Num", "Name", "Memo"]
BALANCE_SHEET_TYPES = (AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY)


class LedgerQueries:
    def __init__(self, session):
        self.session = session

    def lines(self, company_id: int, start: date | None, end: date, account_id: int | None = None) -> list[JournalLine]:
        query = (
            select(JournalLine)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalEntry.entry_date <= end)
        )
        if start is not None:
            query = query.where(JournalEntry.entry_date >= start)
        if account_id is not None:
            query = query.where(JournalLine.account_id == account_id)
        return list(self.session.scalars(query.order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)))

    def entries(self, company_id: int, start: date | None, end: date) -> list[JournalEntry]:
        query = select(JournalEntry).where(JournalEntry.company_id == company_id, JournalEntry.entry_date <= end)
        if start is not None:
            query = query.where(JournalEntry.entry_date >= start)
        return list(self.session.scalars(query.order_by(JournalEntry.entry_date, JournalEntry.id)))

    def accounts(self, company_id: int) -> list[Account]:
        query = select(Account).where(Account.company_id == company_id).order_by(Account.code, Account.name)
        return list(self.session.scalars(query))


def signed_amount(account: Account, line: JournalLine) -> Decimal:
    """Increase of the account's natural balance (debit for assets/expenses, credit for the rest)."""
    if account.account_type.increases_with_debit():
        return line.debit - line.credit
    return line.credit - line.debit


def detail_cells(line_date: date, name, memo: str | None) -> list[str]:
    return [line_date.strftime("%m/%d/%Y"), name.type_label, name.number, name.name, memo or ""]


class GeneralLedgerReport(Report):
    key = "general-ledger"
    title = "General Ledger"
    description = "Every transaction in every account, with running balances."
    group = "For my accountant"
    options = ["account_id"]
    # Which account types to include (None = all).
    account_types: tuple | None = None
    requires_account = False

    def __init__(self, queries: LedgerQueries, names: SourceNames, journal_repository: JournalRepository):
        self.queries = queries
        self.names = names
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        columns = ["Amount", "Balance"]
        if self.requires_account and options.account_id is None:
            return self.make_result(start_date, end_date, [], [], columns=columns, text_columns=DETAIL_COLUMNS, options=options, notes=["Choose an account."])

        opening = {}
        if start_date is not None:
            for totals in self.journal_repository.totals_by_account(company_id, None, start_date - timedelta(days=1)):
                if totals.account.account_type in BALANCE_SHEET_TYPES:
                    opening[totals.account.id] = totals.balance

        lines = self.queries.lines(company_id, start_date, end_date, options.account_id)
        entries = {line.entry.id: line.entry for line in lines}
        names = self.names.for_entries(company_id, list(entries.values()))
        lines_per_account = {}
        for line in lines:
            lines_per_account.setdefault(line.account_id, []).append(line)

        sections = []
        for account in self.queries.accounts(company_id):
            if self.account_types and account.account_type not in self.account_types:
                continue
            if options.account_id is not None and account.id != options.account_id:
                continue
            account_lines = lines_per_account.get(account.id, [])
            start_balance = opening.get(account.id, ZERO)
            if not account_lines and start_balance == 0:
                continue
            balance = start_balance
            rows = []
            if start_balance != 0:
                rows.append(ReportRow(label="Beginning balance", amount=start_balance, cells=["", "", "", "Beginning balance", ""], values=[start_balance, start_balance]))
            for line in account_lines:
                amount = signed_amount(account, line)
                balance += amount
                name = names[line.entry.id]
                rows.append(
                    ReportRow(
                        label=line.entry.memo or name.type_label,
                        amount=amount,
                        account_id=account.id,
                        cells=detail_cells(line.entry.entry_date, name, line.description or line.entry.memo),
                        values=[amount, balance],
                    )
                )
            section = self.make_section(account.name, rows)
            section.totals = [section.total, balance]
            sections.append(section)

        return self.make_result(start_date, end_date, sections, [], columns=columns, text_columns=DETAIL_COLUMNS, options=options)


class AccountQuickReport(GeneralLedgerReport):
    key = "account-quickreport"
    title = "Account QuickReport"
    description = "Every transaction in one account, with its running balance."
    requires_account = True


class BalanceSheetDetailReport(GeneralLedgerReport):
    key = "balance-sheet-detail"
    title = "Balance Sheet Detail"
    description = "The transactions behind each asset, liability and equity balance."
    group = "Business overview"
    account_types = BALANCE_SHEET_TYPES


class JournalReport(Report):
    key = "journal"
    title = "Journal"
    description = "Every journal entry with its debits and credits."
    group = "For my accountant"

    def __init__(self, queries: LedgerQueries, names: SourceNames):
        self.queries = queries
        self.names = names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        entries = self.queries.entries(company_id, start_date, end_date)
        names = self.names.for_entries(company_id, entries)
        sections = []
        total_debit = ZERO
        for entry in entries:
            name = names[entry.id]
            rows = []
            for line in entry.lines:
                rows.append(
                    ReportRow(
                        label=line.account.name,
                        amount=line.debit,
                        account_id=line.account_id,
                        cells=[line.account.name, line.description or ""],
                        values=[line.debit or None, line.credit or None],
                    )
                )
                total_debit += line.debit
            title = f"{entry.entry_date:%m/%d/%Y}  {name.type_label} {name.number}  {name.name}".strip()
            section = self.make_section(title, rows)
            section.totals = [sum((line.debit for line in entry.lines), ZERO), sum((line.credit for line in entry.lines), ZERO)]
            sections.append(section)
        summary = [ReportRow(label="Total", amount=total_debit, values=[total_debit, total_debit])]
        return self.make_result(start_date, end_date, sections, summary, columns=["Debit", "Credit"], text_columns=["Account", "Memo"], options=options)


class TransactionListReport(Report):
    key = "transaction-list"
    title = "Transaction List by Date"
    description = "Every transaction in the period, one line each."
    group = "For my accountant"
    options = ["customer_id", "vendor_id"]

    def __init__(self, queries: LedgerQueries, names: SourceNames):
        self.queries = queries
        self.names = names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        entries = self.queries.entries(company_id, start_date, end_date)
        names = self.names.for_entries(company_id, entries)
        rows = []
        for entry in entries:
            name = names[entry.id]
            if options.customer_id is not None and name.customer_id != options.customer_id:
                continue
            if options.vendor_id is not None and name.vendor_id != options.vendor_id:
                continue
            amount = sum((line.debit for line in entry.lines), ZERO)
            rows.append(
                ReportRow(
                    label=entry.memo or name.type_label,
                    amount=amount,
                    cells=[entry.entry_date.strftime("%m/%d/%Y"), name.type_label, name.number, name.name, entry.memo or ""],
                )
            )
        section = self.make_section("Transactions", rows)
        return self.make_result(start_date, end_date, [section], [], text_columns=DETAIL_COLUMNS, options=options)
