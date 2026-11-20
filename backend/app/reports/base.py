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

from app.schemas.report import ReportOptions, ReportResult, ReportRow, ReportSection

# Groups on the Reports page, in the order they are shown.
REPORT_GROUPS = [
    "Business overview",
    "Who owes you",
    "Sales and customers",
    "What you owe",
    "Expenses and vendors",
    "Sales tax",
    "Employees",
    "Inventory",
    "For my accountant",
]


class Report(ABC):
    key = ""
    title = ""
    description = ""
    group = "Business overview"
    # False for "as of" reports like the Balance Sheet that ignore the start date.
    uses_start_date = True
    # Option names this report understands (see ReportOptions).
    options: list[str] = []
    # Options this report starts with.
    defaults: dict[str, str] = {}

    @abstractmethod
    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        """Build the report for one company and period."""

    # ----- helpers shared by all reports -----

    def make_section(self, title: str, rows: list[ReportRow]) -> ReportSection:
        total = Decimal("0.00")
        for row in rows:
            total += row.amount
        totals = self.column_totals(rows)
        return ReportSection(title=title, rows=rows, total=total, totals=totals)

    def column_totals(self, rows: list[ReportRow]) -> list[Decimal | None]:
        """Add up each value column. A column with any blank (None) value stays blank, e.g. "% change"."""
        if not rows or not rows[0].values:
            return []
        totals = [Decimal("0.00")] * len(rows[0].values)
        for row in rows:
            for index, value in enumerate(row.values):
                if value is not None and totals[index] is not None:
                    totals[index] += value
        return totals

    def kind_of_column(self, label: str) -> str:
        if label.startswith("%"):
            return "percent"
        if label in ("Quantity", "Hours"):
            return "number"
        return "money"

    def make_result(
        self,
        start_date: date | None,
        end_date: date,
        sections: list[ReportSection],
        summary: list[ReportRow],
        columns: list[str] | None = None,
        text_columns: list[str] | None = None,
        options: ReportOptions | None = None,
        notes: list[str] | None = None,
    ) -> ReportResult:
        if not self.uses_start_date:
            start_date = None
        return ReportResult(
            key=self.key,
            title=self.title,
            start_date=start_date,
            end_date=end_date,
            sections=sections,
            summary=summary,
            columns=columns or [],
            column_kinds=[self.kind_of_column(label) for label in columns or []],
            text_columns=text_columns or [],
            basis=options.basis if options else "accrual",
            notes=notes or [],
        )
