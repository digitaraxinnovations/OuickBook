from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.reports.base import Report
from app.schemas.report import ReportInfo, ReportResult


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
