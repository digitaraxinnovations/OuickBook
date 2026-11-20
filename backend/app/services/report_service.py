from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.reports.base import REPORT_GROUPS, Report
from app.schemas.report import COLUMN_CHOICES, COMPARE_CHOICES, ReportInfo, ReportOptions, ReportResult


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
                    group=report.group,
                    options=list(report.options),
                    defaults=dict(report.defaults),
                )
            )
        result.sort(key=lambda info: REPORT_GROUPS.index(info.group) if info.group in REPORT_GROUPS else len(REPORT_GROUPS))
        return result

    def get(self, key: str) -> Report:
        report = self.reports.get(key)
        if report is None:
            raise NotFoundError(f'Report "{key}" does not exist.')
        return report

    def run(
        self,
        key: str,
        company_id: int,
        start_date: date | None,
        end_date: date | None,
        options: ReportOptions | None = None,
    ) -> ReportResult:
        report = self.get(key)
        if options is None:
            options = ReportOptions()
        # Options the user did not set take the report's own defaults (e.g. "by month").
        for name, value in report.defaults.items():
            if name not in options.model_fields_set:
                setattr(options, name, value)
        if options.column_by not in COLUMN_CHOICES:
            raise BusinessRuleError("Unknown column choice.")
        if options.compare is not None and options.compare not in COMPARE_CHOICES:
            raise BusinessRuleError("Unknown comparison.")

        today = date.today()
        if end_date is None:
            end_date = today
        if start_date is None and report.uses_start_date:
            start_date = date(end_date.year, 1, 1)
        if start_date is not None and start_date > end_date:
            raise BusinessRuleError("The start date must be on or before the end date.")

        return report.generate(company_id, start_date, end_date, options)
