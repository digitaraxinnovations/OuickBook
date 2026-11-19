from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.reports.balance_sheet import BalanceSheetReport
from app.reports.base import Report
from app.reports.profit_and_loss import ProfitAndLossReport
from app.reports.receivables_aging import ReceivablesAgingReport
from app.reports.trial_balance import TrialBalanceReport
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.report import ReportInfo, ReportResult


def build_default_reports(journal_repository: JournalRepository, invoice_repository: InvoiceRepository) -> list[Report]:
    """The list of available reports. Add new reports here."""
    return [
        ProfitAndLossReport(journal_repository),
        BalanceSheetReport(journal_repository),
        TrialBalanceReport(journal_repository),
        ReceivablesAgingReport(invoice_repository),
    ]


class ReportService:
    """Finds a report by its key and runs it. Knows nothing about how each report works."""

    def __init__(self, reports: list[Report]):
        self.reports = {}
        for report in reports:
            self.reports[report.key] = report

    def list_reports(self) -> list[ReportInfo]:
        result = []
        for report in self.reports.values():
            result.append(
                ReportInfo(
                    key=report.key,
                    title=report.title,
                    description=report.description,
                    uses_start_date=report.uses_start_date,
                )
            )
        return result

    def run(self, key: str, company_id: int, start_date: date | None, end_date: date | None) -> ReportResult:
        report = self.reports.get(key)
        if report is None:
            raise NotFoundError(f'Report "{key}" does not exist.')

        today = date.today()
        if end_date is None:
            end_date = today
        if start_date is None and report.uses_start_date:
            start_date = date(end_date.year, 1, 1)
        if start_date is not None and start_date > end_date:
            raise BusinessRuleError("The start date must be on or before the end date.")

        return report.generate(company_id, start_date, end_date)
