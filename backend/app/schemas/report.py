"""
Every report returns the same simple shape, so the frontend can draw
any report with one generic component.

- A report has sections; each section has rows and a total.
- A row has a label and an amount. Multi-column reports (by month,
  comparisons...) also fill `values`, one per entry in ReportResult.columns.
- Detail reports (general ledger, transaction lists...) put text such as
  date, number and name in `cells`, one per entry in ReportResult.text_columns.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

# What the "columns" option can be (Profit and Loss).
COLUMN_CHOICES = ("total", "month", "quarter", "year", "customer", "vendor", "class", "location")
# What the "compare" option can be.
COMPARE_CHOICES = ("previous_period", "previous_year")


class ReportOptions(BaseModel):
    """Choices the user can make on a report. Each report uses the ones it supports."""

    # "accrual" (when invoiced / billed) or "cash" (when paid)
    basis: str = Field(default="accrual", pattern="^(accrual|cash)$")
    # Split amounts into columns (see COLUMN_CHOICES).
    column_by: str = "total"
    # Add a column with an earlier period and the change.
    compare: str | None = None
    # Filters
    class_id: int | None = None
    location_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    project_id: int | None = None
    account_id: int | None = None


class ReportRow(BaseModel):
    label: str
    amount: Decimal
    account_id: int | None = None
    # Text columns of detail reports (see ReportResult.text_columns).
    cells: list[str] = Field(default_factory=list)
    # Amount columns of multi-column reports (see ReportResult.columns).
    values: list[Decimal | None] = Field(default_factory=list)


class ReportSection(BaseModel):
    title: str
    rows: list[ReportRow]
    total: Decimal
    totals: list[Decimal | None] = Field(default_factory=list)


class ReportResult(BaseModel):
    key: str
    title: str
    start_date: date | None
    end_date: date
    sections: list[ReportSection]
    # Bottom lines such as "Net income" or "Total liabilities and equity".
    summary: list[ReportRow]
    # Amount column headings. Empty = one column ("amount").
    columns: list[str] = Field(default_factory=list)
    # How to show each column: "money", "number" or "percent".
    column_kinds: list[str] = Field(default_factory=list)
    # Text column headings shown before the amounts (detail reports).
    text_columns: list[str] = Field(default_factory=list)
    basis: str = "accrual"
    # Short notes shown under the report.
    notes: list[str] = Field(default_factory=list)


class ReportInfo(BaseModel):
    key: str
    title: str
    description: str
    uses_start_date: bool
    # Where the report is listed on the Reports page.
    group: str
    # Which options the report supports, e.g. ["basis", "column_by", "customer_id"].
    options: list[str]
    # Options this entry starts with (e.g. "Profit and Loss by Month" = column_by month).
    defaults: dict[str, str] = Field(default_factory=dict)


# ---------- saved reports and schedules ----------


class SavedReportWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    report_key: str = Field(min_length=1, max_length=60)
    # "this_month", "last_month", "this_quarter", "this_year", "last_year", "custom"
    date_range: str = Field(default="this_year", max_length=20)
    start_date: date | None = None
    end_date: date | None = None
    options: ReportOptions = Field(default_factory=ReportOptions)


class SavedReportRead(BaseModel):
    id: int
    name: str
    report_key: str
    date_range: str
    start_date: date | None
    end_date: date | None
    options: ReportOptions


class ReportScheduleWrite(BaseModel):
    saved_report_id: int
    # "DAILY", "WEEKLY", "MONTHLY"
    frequency: str = Field(pattern="^(DAILY|WEEKLY|MONTHLY)$")
    next_send_date: date
    recipients: list[str] = Field(min_length=1)
    # "pdf", "csv" or "xlsx"
    file_format: str = Field(default="pdf", pattern="^(pdf|csv|xlsx)$")
    is_active: bool = True


class ReportScheduleRead(BaseModel):
    id: int
    saved_report_id: int
    frequency: str
    next_send_date: date
    recipients: list[str]
    file_format: str
    is_active: bool
    last_sent_at: date | None
