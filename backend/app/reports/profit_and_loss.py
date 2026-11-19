from datetime import date

from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportResult, ReportRow


class ProfitAndLossReport(Report):
    key = "profit-and-loss"
    title = "Profit and Loss"
    description = "Income minus expenses for a period. Shows whether you made money."

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        income_rows = []
        expense_rows = []

        for totals in self.journal_repository.totals_by_account(company_id, start_date, end_date):
            if totals.balance == 0:
                continue
            row = ReportRow(label=totals.account.name, amount=totals.balance, account_id=totals.account.id)
            if totals.account.account_type == AccountType.INCOME:
                income_rows.append(row)
            elif totals.account.account_type == AccountType.EXPENSE:
                expense_rows.append(row)

        income = self.make_section("Income", income_rows)
        expenses = self.make_section("Expenses", expense_rows)
        net_income = income.total - expenses.total

        return self.make_result(
            start_date,
            end_date,
            sections=[income, expenses],
            summary=[ReportRow(label="Net income", amount=net_income)],
        )
