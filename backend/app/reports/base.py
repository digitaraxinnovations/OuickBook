"""
Base class for reports.

To add a new report:
  1. Create a class that inherits from Report and implements generate().
  2. Add it to build_reports() in api/deps.py.
No other code has to change (Open/Closed principle).
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.schemas.report import ReportResult, ReportRow, ReportSection


class Report(ABC):
    key = ""
    title = ""
    description = ""
    # False for "as of" reports like the Balance Sheet that ignore the start date.
    uses_start_date = True

    @abstractmethod
    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        """Build the report for one company and period."""

    # ----- helpers shared by all reports -----

    def make_section(self, title: str, rows: list[ReportRow]) -> ReportSection:
        total = Decimal("0.00")
        for row in rows:
            total += row.amount
        return ReportSection(title=title, rows=rows, total=total)

    def make_result(self, start_date: date | None, end_date: date, sections: list[ReportSection], summary: list[ReportRow]) -> ReportResult:
        if not self.uses_start_date:
            start_date = None
        return ReportResult(
            key=self.key,
            title=self.title,
            start_date=start_date,
            end_date=end_date,
            sections=sections,
            summary=summary,
        )
