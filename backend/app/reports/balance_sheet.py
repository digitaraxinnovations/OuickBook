from datetime import date
from decimal import Decimal

from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportResult, ReportRow


class BalanceSheetReport(Report):
    key = "balance-sheet"
    title = "Balance Sheet"
    description = "What you own (assets), what you owe (liabilities) and your equity on a date."
    uses_start_date = False

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        asset_rows = []
        liability_rows = []
        equity_rows = []
        net_income = Decimal("0.00")

        # start_date=None -> everything from the beginning up to end_date
        for totals in self.journal_repository.totals_by_account(company_id, None, end_date):
            account_type = totals.account.account_type
            row = ReportRow(label=totals.account.name, amount=totals.balance, account_id=totals.account.id)

            if account_type == AccountType.INCOME:
                net_income += totals.balance
            elif account_type == AccountType.EXPENSE:
                net_income -= totals.balance
            elif totals.balance == 0:
                continue
            elif account_type == AccountType.ASSET:
                asset_rows.append(row)
            elif account_type == AccountType.LIABILITY:
                liability_rows.append(row)
            elif account_type == AccountType.EQUITY:
                equity_rows.append(row)

        # Profit that has not been closed to Retained Earnings yet still belongs to the owners.
        if net_income != 0:
            equity_rows.append(ReportRow(label="Net income", amount=net_income))

        assets = self.make_section("Assets", asset_rows)
        liabilities = self.make_section("Liabilities", liability_rows)
        equity = self.make_section("Equity", equity_rows)

        return self.make_result(
            start_date,
            end_date,
            sections=[assets, liabilities, equity],
            summary=[
                ReportRow(label="Total assets", amount=assets.total),
                ReportRow(label="Total liabilities and equity", amount=liabilities.total + equity.total),
            ],
        )
