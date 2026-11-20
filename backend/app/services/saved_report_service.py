"""
Saved reports, exporting reports to files, and emailing them on a schedule.
"""

from datetime import date, timedelta

from sqlalchemy import select

from app.core.dates import add_months
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.integrations.email import OutgoingEmail
from app.models import ReportSchedule, SavedReport
from app.reports.exporters import EXPORTERS
from app.repositories.company_repository import CompanyRepository
from app.schemas.report import (
    ReportOptions,
    ReportResult,
    ReportScheduleRead,
    ReportScheduleWrite,
    SavedReportRead,
    SavedReportWrite,
)
from app.services.base import BaseService
from app.services.email_service import EmailService
from app.services.report_service import ReportService

DATE_RANGES = ("this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year", "custom")


def resolve_date_range(date_range: str, today: date, start: date | None = None, end: date | None = None) -> tuple[date | None, date]:
    """Turn "last_month" etc. into dates, counted from `today`."""
    if date_range == "custom":
        return start, end or today
    if date_range == "this_month":
        first = today.replace(day=1)
        return first, add_months(first, 1) - timedelta(days=1)
    if date_range == "last_month":
        first = add_months(today.replace(day=1), -1)
        return first, today.replace(day=1) - timedelta(days=1)
    quarter_first = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    if date_range == "this_quarter":
        return quarter_first, add_months(quarter_first, 3) - timedelta(days=1)
    if date_range == "last_quarter":
        first = add_months(quarter_first, -3)
        return first, quarter_first - timedelta(days=1)
    if date_range == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    if date_range == "last_year":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    raise BusinessRuleError("Unknown date range.")


class ExportedFile:
    def __init__(self, filename: str, media_type: str, content: bytes):
        self.filename = filename
        self.media_type = media_type
        self.content = content


class SavedReportService(BaseService):
    def __init__(self, session, reports: ReportService, company_repository: CompanyRepository, email_service: EmailService):
        super().__init__(session)
        self.reports = reports
        self.company_repository = company_repository
        self.email_service = email_service

    # ---------- exporting ----------

    def export(self, company_id: int, result: ReportResult, file_format: str) -> ExportedFile:
        exporter = EXPORTERS.get(file_format)
        if exporter is None:
            raise BusinessRuleError("Export as pdf, csv or xlsx.")
        company = self.company_repository.get(company_id)
        content = exporter.export(result, company.name)
        filename = f"{result.title} {result.end_date}.{exporter.file_extension}".replace(" ", "-").replace("/", "-")
        return ExportedFile(filename, exporter.media_type, content)

    # ---------- saved reports ----------

    def list(self, company_id: int) -> list[SavedReportRead]:
        query = select(SavedReport).where(SavedReport.company_id == company_id).order_by(SavedReport.name)
        return [self.to_read(record) for record in self.session.scalars(query)]

    def get_record(self, company_id: int, saved_id: int) -> SavedReport:
        record = self.session.get(SavedReport, saved_id)
        if record is None or record.company_id != company_id:
            raise NotFoundError("Saved report not found.")
        return record

    def save(self, company_id: int, data: SavedReportWrite, saved_id: int | None = None) -> SavedReportRead:
        self.reports.get(data.report_key)
        if data.date_range not in DATE_RANGES:
            raise BusinessRuleError("Unknown date range.")
        if data.date_range == "custom" and data.end_date is None:
            raise BusinessRuleError("Enter the end date of the custom range.")
        record = SavedReport(company_id=company_id) if saved_id is None else self.get_record(company_id, saved_id)
        record.name = data.name
        record.report_key = data.report_key
        record.date_range = data.date_range
        record.start_date = data.start_date
        record.end_date = data.end_date
        record.options = data.options.model_dump(exclude_unset=True)
        if saved_id is None:
            self.session.add(record)
        self.commit()
        return self.to_read(record)

    def delete(self, company_id: int, saved_id: int) -> None:
        record = self.get_record(company_id, saved_id)
        for schedule in self.schedules_of(company_id, saved_id):
            self.session.delete(schedule)
        self.session.delete(record)
        self.commit()

    def run(self, company_id: int, saved_id: int, today: date | None = None) -> ReportResult:
        record = self.get_record(company_id, saved_id)
        start, end = resolve_date_range(record.date_range, today or date.today(), record.start_date, record.end_date)
        options = ReportOptions(**record.options)
        result = self.reports.run(record.report_key, company_id, start, end, options)
        result.title = f"{record.name} ({result.title})" if record.name != result.title else result.title
        return result

    def to_read(self, record: SavedReport) -> SavedReportRead:
        return SavedReportRead(
            id=record.id,
            name=record.name,
            report_key=record.report_key,
            date_range=record.date_range,
            start_date=record.start_date,
            end_date=record.end_date,
            options=ReportOptions(**record.options),
        )

    # ---------- schedules ----------

    def schedules_of(self, company_id: int, saved_id: int | None = None) -> list[ReportSchedule]:
        query = select(ReportSchedule).where(ReportSchedule.company_id == company_id)
        if saved_id is not None:
            query = query.where(ReportSchedule.saved_report_id == saved_id)
        return list(self.session.scalars(query.order_by(ReportSchedule.next_send_date)))

    def list_schedules(self, company_id: int) -> list[ReportScheduleRead]:
        return [ReportScheduleRead.model_validate(record, from_attributes=True) for record in self.schedules_of(company_id)]

    def save_schedule(self, company_id: int, data: ReportScheduleWrite, schedule_id: int | None = None) -> ReportScheduleRead:
        self.get_record(company_id, data.saved_report_id)
        for address in data.recipients:
            if "@" not in address:
                raise BusinessRuleError(f'"{address}" is not an email address.')
        if schedule_id is None:
            record = ReportSchedule(company_id=company_id)
        else:
            record = self.session.get(ReportSchedule, schedule_id)
            if record is None or record.company_id != company_id:
                raise NotFoundError("Schedule not found.")
        for field_name, value in data.model_dump().items():
            setattr(record, field_name, value)
        if schedule_id is None:
            self.session.add(record)
        self.commit()
        return ReportScheduleRead.model_validate(record, from_attributes=True)

    def delete_schedule(self, company_id: int, schedule_id: int) -> None:
        record = self.session.get(ReportSchedule, schedule_id)
        if record is None or record.company_id != company_id:
            raise NotFoundError("Schedule not found.")
        self.session.delete(record)
        self.commit()

    def send_due(self, company_id: int, today: date) -> int:
        """Email every active schedule that is due. Returns how many emails were sent."""
        sent = 0
        for schedule in self.schedules_of(company_id):
            if not schedule.is_active or schedule.next_send_date > today:
                continue
            result = self.run(company_id, schedule.saved_report_id, today)
            exported = self.export(company_id, result, schedule.file_format)
            for address in schedule.recipients:
                email = OutgoingEmail(
                    to=address,
                    subject=result.title,
                    body=f"Attached is {result.title}, sent automatically by Ledgerly.",
                    attachment_name=exported.filename,
                    attachment=exported.content,
                )
                self.email_service.send(company_id, email, related_type="REPORT_SCHEDULE", related_id=schedule.id)
                sent += 1
            schedule.last_sent_at = today
            schedule.next_send_date = self.next_date(schedule.frequency, schedule.next_send_date, today)
        self.commit()
        return sent

    def next_date(self, frequency: str, current: date, today: date) -> date:
        next_send = current
        while next_send <= today:
            if frequency == "DAILY":
                next_send = next_send + timedelta(days=1)
            elif frequency == "WEEKLY":
                next_send = next_send + timedelta(days=7)
            else:
                next_send = add_months(next_send, 1)
        return next_send
