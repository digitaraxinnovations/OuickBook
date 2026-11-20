"""
Saved (custom) reports and report schedules.

- SavedReport:    a report with its options and date range, under your own name.
- ReportSchedule: emails a saved report as a PDF, CSV or Excel file every
                  day, week or month (sent by the daily job).
"""

from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin


class SavedReport(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "saved_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    report_key: Mapped[str] = mapped_column(String(60))
    # "this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year", "custom"
    date_range: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # ReportOptions as a dictionary.
    options: Mapped[dict] = mapped_column(JSON)


class ReportSchedule(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    saved_report_id: Mapped[int] = mapped_column(ForeignKey("saved_reports.id", ondelete="CASCADE"), index=True)
    # "DAILY", "WEEKLY" or "MONTHLY"
    frequency: Mapped[str] = mapped_column(String(20))
    next_send_date: Mapped[date] = mapped_column(Date)
    recipients: Mapped[list] = mapped_column(JSON)
    # "pdf", "csv" or "xlsx"
    file_format: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=True)
    last_sent_at: Mapped[date | None] = mapped_column(Date)

    saved_report: Mapped[SavedReport] = relationship()
