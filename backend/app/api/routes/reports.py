from datetime import date

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, get_dashboard_service, get_forecast_service, get_report_service, get_saved_report_service
from app.models import User
from app.schemas.dashboard import DashboardSummary
from app.schemas.forecast import ForecastRead
from app.schemas.report import (
    ReportInfo,
    ReportOptions,
    ReportResult,
    ReportScheduleRead,
    ReportScheduleWrite,
    SavedReportRead,
    SavedReportWrite,
)
from app.services.dashboard_service import DashboardService
from app.services.forecast_service import ForecastService
from app.services.report_service import ReportService
from app.services.saved_report_service import ExportedFile, SavedReportService

router = APIRouter(tags=["Reports & Dashboard"])


def report_options(
    basis: str | None = None,
    column_by: str | None = None,
    compare: str | None = None,
    class_id: int | None = None,
    location_id: int | None = None,
    customer_id: int | None = None,
    vendor_id: int | None = None,
    project_id: int | None = None,
    account_id: int | None = None,
) -> ReportOptions:
    """Report options from the query string. Only the ones given count as "set" (so defaults still apply)."""
    given = {}
    for name, value in (
        ("basis", basis),
        ("column_by", column_by),
        ("compare", compare),
        ("class_id", class_id),
        ("location_id", location_id),
        ("customer_id", customer_id),
        ("vendor_id", vendor_id),
        ("project_id", project_id),
        ("account_id", account_id),
    ):
        if value is not None:
            given[name] = value
    return ReportOptions(**given)


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_summary(user.company_id, start_date, end_date)


@router.get("/reports", response_model=list[ReportInfo])
def list_reports(
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return service.list_reports()


@router.get("/reports/{report_key}", response_model=ReportResult)
def run_report(
    report_key: str,
    start_date: date | None = None,
    end_date: date | None = None,
    options: ReportOptions = Depends(report_options),
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return service.run(report_key, user.company_id, start_date, end_date, options, *company_defaults(user))



def company_defaults(user: User) -> tuple[str, int]:
    """(default basis, fiscal year start month) from the company's advanced settings."""
    company = user.company
    return company.accounting_method.lower(), company.fiscal_year_start_month


def file_response(exported: ExportedFile) -> Response:
    disposition = "inline" if exported.media_type == "application/pdf" else "attachment"
    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{exported.filename}"'},
    )


@router.get("/reports/{report_key}/export")
def export_report(
    report_key: str,
    file_format: str = "pdf",
    start_date: date | None = None,
    end_date: date | None = None,
    options: ReportOptions = Depends(report_options),
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
    saved: SavedReportService = Depends(get_saved_report_service),
):
    """The report as a PDF, CSV or Excel (xlsx) file."""
    result = service.run(report_key, user.company_id, start_date, end_date, options, *company_defaults(user))
    return file_response(saved.export(user.company_id, result, file_format))


# ---------- saved (custom) reports ----------

@router.get("/saved-reports", response_model=list[SavedReportRead])
def list_saved_reports(user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.list(user.company_id)


@router.post("/saved-reports", response_model=SavedReportRead, status_code=status.HTTP_201_CREATED)
def create_saved_report(data: SavedReportWrite, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.save(user.company_id, data)


@router.put("/saved-reports/{saved_id}", response_model=SavedReportRead)
def update_saved_report(saved_id: int, data: SavedReportWrite, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.save(user.company_id, data, saved_id)


@router.delete("/saved-reports/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_report(saved_id: int, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    saved.delete(user.company_id, saved_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/saved-reports/{saved_id}/run", response_model=ReportResult)
def run_saved_report(saved_id: int, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.run(user.company_id, saved_id)


# ---------- scheduled emails ----------

@router.get("/report-schedules", response_model=list[ReportScheduleRead])
def list_schedules(user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.list_schedules(user.company_id)


@router.post("/report-schedules", response_model=ReportScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(data: ReportScheduleWrite, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.save_schedule(user.company_id, data)


@router.put("/report-schedules/{schedule_id}", response_model=ReportScheduleRead)
def update_schedule(schedule_id: int, data: ReportScheduleWrite, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    return saved.save_schedule(user.company_id, data, schedule_id)


@router.delete("/report-schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    saved.delete_schedule(user.company_id, schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/report-schedules/send-due")
def send_due_reports(user: User = Depends(get_current_user), saved: SavedReportService = Depends(get_saved_report_service)):
    """Send every schedule due today now (the daily job does this automatically)."""
    return {"sent": saved.send_due(user.company_id, date.today())}


@router.get("/forecast", response_model=ForecastRead)
def cash_flow_forecast(
    user: User = Depends(get_current_user),
    service: ForecastService = Depends(get_forecast_service),
):
    """The expected bank balance for the coming days."""
    return service.build(user.company_id)
