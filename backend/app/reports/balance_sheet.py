"""
Balance Sheet: assets, liabilities and equity on a date.

Options:
- compare: previous_year (same date last year) or previous_period (end of the month before)
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.dates import add_months
from app.core.money import ZERO, to_money
from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow, ReportSection


class BalanceSheetReport(Report):
    key = "balance-sheet"
    title = "Balance Sheet"
    description = "What you own (assets), what you owe (liabilities) and your equity on a date."
    uses_start_date = False
    options = ["compare"]

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def balances_on(self, company_id: int, on_date: date) -> tuple[dict, Decimal]:
        """({(section, account id, name): balance}, net income not yet closed)."""
        amounts = {}
        net_income = ZERO
        # start_date=None -> everything from the beginning up to the date
        for totals in self.journal_repository.totals_by_account(company_id, None, on_date):
            account_type = totals.account.account_type
            if account_type == AccountType.INCOME:
                net_income += totals.balance
            elif account_type == AccountType.EXPENSE:
                net_income -= totals.balance
            elif totals.balance != 0:
                section = {AccountType.ASSET: "Assets", AccountType.LIABILITY: "Liabilities", AccountType.EQUITY: "Equity"}[account_type]
                amounts[(section, totals.account.id, totals.account.name)] = totals.balance
        return amounts, net_income

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        current, net_income = self.balances_on(company_id, end_date)
        # Profit that has not been closed to Retained Earnings yet still belongs to the owners.
        if net_income != 0:
            current[("Equity", None, "Net income")] = net_income

        if not options.compare:
            sections = []
            for title in ("Assets", "Liabilities", "Equity"):
                rows = [ReportRow(label=key[2], amount=amount, account_id=key[1]) for key, amount in current.items() if key[0] == title]
                sections.append(self.make_section(title, rows))
            return self.make_result(start_date, end_date, sections, self.summary(sections), options=options)

        prior_date = add_months(end_date, -12) if options.compare == "previous_year" else end_date.replace(day=1) - timedelta(days=1)
        prior, prior_income = self.balances_on(company_id, prior_date)
        if prior_income != 0:
            prior[("Equity", None, "Net income")] = prior_income

        sections = []
        for title in ("Assets", "Liabilities", "Equity"):
            keys = sorted({key for key in list(current) + list(prior) if key[0] == title}, key=lambda key: (key[2] == "Net income", key[2]))
            rows = []
            for key in keys:
                now = current.get(key, ZERO)
                before = prior.get(key, ZERO)
                rows.append(ReportRow(label=key[2], amount=now, account_id=key[1], values=self.compare_values(now, before)))
            section = self.make_section(title, rows)
            section.totals = self.compare_values(section.total, sum((row.values[1] for row in rows), ZERO))
            sections.append(section)
        labels = [f"As of {end_date:%b %d, %Y}", f"As of {prior_date:%b %d, %Y}", "$ change", "% change"]
        return self.make_result(start_date, end_date, sections, self.summary(sections), columns=labels, options=options)

    def summary(self, sections: list[ReportSection]) -> list[ReportRow]:
        assets, liabilities, equity = sections
        total_assets = ReportRow(label="Total assets", amount=assets.total)
        other_side = ReportRow(label="Total liabilities and equity", amount=liabilities.total + equity.total)
        if assets.totals:
            total_assets.values = list(assets.totals)
            other_side.values = self.compare_values(liabilities.totals[0] + equity.totals[0], liabilities.totals[1] + equity.totals[1])
        return [total_assets, other_side]

    def compare_values(self, now: Decimal, before: Decimal) -> list[Decimal | None]:
        change = now - before
        percent = to_money(change * Decimal("100") / abs(before)) if before != 0 else None
        return [now, before, change, percent]


class BalanceSheetComparisonReport(BalanceSheetReport):
    key = "balance-sheet-comparison"
    title = "Balance Sheet Comparison"
    description = "Your balance sheet today next to the same date last year."
    defaults = {"compare": "previous_year"}
