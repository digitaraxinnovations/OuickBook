"""
Statement of Cash Flows (indirect method).

Starts from net income and adds the change in every other balance sheet
account, sorted into:
- Operating:  receivables, payables, credit cards, inventory, sales tax, payroll...
- Investing:  fixed assets
- Financing:  loans and owner's equity
The total is the change in cash (bank accounts and Undeposited Funds).
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.money import ZERO
from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow
from app.seed.default_accounts import DetailType, SystemAccount

INVESTING_DETAILS = ("Fixed Assets", "Furniture & Fixtures", "Machinery & Equipment", "Vehicles", "Buildings", "Land")
FINANCING_DETAILS = ("Long Term Liabilities", "Notes Payable", "Loan Payable")


def is_cash(account) -> bool:
    return account.detail_type == DetailType.BANK or account.system_key == SystemAccount.UNDEPOSITED_FUNDS


def activity_of(account) -> str:
    if account.account_type == AccountType.EQUITY:
        return "Financing activities"
    if account.account_type == AccountType.ASSET and account.detail_type in INVESTING_DETAILS:
        return "Investing activities"
    if account.account_type == AccountType.LIABILITY and account.detail_type in FINANCING_DETAILS:
        return "Financing activities"
    return "Operating activities"


class CashFlowReport(Report):
    key = "cash-flow"
    title = "Statement of Cash Flows"
    description = "Where your cash came from and went: operations, investing and financing."
    group = "Business overview"

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        start = start_date or date(end_date.year, 1, 1)
        before = start - timedelta(days=1)

        change = {}
        accounts = {}
        for totals in self.journal_repository.totals_by_account(company_id, start, end_date):
            accounts[totals.account.id] = totals.account
            change[totals.account.id] = totals.debit - totals.credit

        net_income = ZERO
        rows = {"Operating activities": [], "Investing activities": [], "Financing activities": []}
        for account_id, debit_minus_credit in change.items():
            account = accounts[account_id]
            if account.account_type in (AccountType.INCOME, AccountType.EXPENSE):
                net_income -= debit_minus_credit
                continue
            if is_cash(account):
                continue
            # More assets use cash; more liabilities or equity bring cash in.
            effect = -debit_minus_credit
            if effect != 0:
                rows[activity_of(account)].append(ReportRow(label=account.name, amount=effect, account_id=account.id))

        rows["Operating activities"].insert(0, ReportRow(label="Net income", amount=net_income))
        sections = [self.make_section(title, section_rows) for title, section_rows in rows.items()]
        net_change = sum((section.total for section in sections), ZERO)

        cash_at_start = self.cash_on(company_id, before)
        summary = [
            ReportRow(label="Net cash increase for the period", amount=net_change),
            ReportRow(label="Cash at beginning of period", amount=cash_at_start),
            ReportRow(label="Cash at end of period", amount=cash_at_start + net_change),
        ]
        return self.make_result(start_date, end_date, sections, summary, options=options)

    def cash_on(self, company_id: int, on_date: date) -> Decimal:
        total = ZERO
        for totals in self.journal_repository.totals_by_account(company_id, None, on_date):
            if is_cash(totals.account):
                total += totals.debit - totals.credit
        return total
