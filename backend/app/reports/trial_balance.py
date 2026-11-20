from datetime import date

from app.reports.base import Report
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow


class TrialBalanceReport(Report):
    key = "trial-balance"
    group = "For my accountant"
    title = "Trial Balance"
    description = "Every account's debit or credit balance. Total debits must equal total credits."
    uses_start_date = False

    def __init__(self, journal_repository: JournalRepository):
        self.journal_repository = journal_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        debit_rows = []
        credit_rows = []

        for totals in self.journal_repository.totals_by_account(company_id, None, end_date):
            net = totals.debit - totals.credit
            if net > 0:
                debit_rows.append(ReportRow(label=totals.account.name, amount=net, account_id=totals.account.id))
            elif net < 0:
                credit_rows.append(ReportRow(label=totals.account.name, amount=-net, account_id=totals.account.id))

        debits = self.make_section("Debit balances", debit_rows)
        credits = self.make_section("Credit balances", credit_rows)

        return self.make_result(
            start_date,
            end_date,
            sections=[debits, credits],
            summary=[
                ReportRow(label="Total debits", amount=debits.total),
                ReportRow(label="Total credits", amount=credits.total),
            ],
        )
