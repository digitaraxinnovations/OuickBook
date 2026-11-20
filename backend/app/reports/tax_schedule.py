"""
Tax Schedule Summary: the Profit and Loss grouped by income tax category
(Schedule C lines), ready to copy onto a tax return. Accounts without a
category are listed separately so nothing is missed.
"""

from datetime import date

from app.core.money import ZERO
from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportResult, ReportRow
from app.seed.default_accounts import TAX_LINES

UNASSIGNED = "Not assigned to a tax category"


class TaxScheduleReport(Report):
    key = "tax-schedule"
    title = "Tax Schedule Summary"
    description = "Income and expenses grouped by income tax category (Schedule C lines)."

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        # amount_per_line[tax_line] = amount; expenses are kept negative so the net adds up.
        amount_per_line = {}
        unassigned_rows = []
        net_profit = ZERO

        for totals in self.journal_repository.totals_by_account(company_id, start_date, end_date):
            account = totals.account
            if totals.balance == 0 or account.account_type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue
            amount = totals.balance
            if account.account_type == AccountType.EXPENSE:
                amount = -amount
            net_profit += amount

            if account.tax_line is None:
                unassigned_rows.append(ReportRow(label=account.name, amount=amount, account_id=account.id))
            else:
                amount_per_line[account.tax_line] = amount_per_line.get(account.tax_line, ZERO) + amount

        rows = []
        for tax_line, label in TAX_LINES.items():
            if tax_line in amount_per_line:
                rows.append(ReportRow(label=label, amount=amount_per_line[tax_line]))

        sections = [self.make_section("Schedule C (expenses shown as negative)", rows)]
        if unassigned_rows:
            sections.append(self.make_section(UNASSIGNED, unassigned_rows))
        summary = [ReportRow(label="Net profit", amount=net_profit)]
        return self.make_result(start_date, end_date, sections, summary)
