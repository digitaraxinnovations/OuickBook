from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_dashboard_service, get_report_service
from app.models import User
from app.schemas.dashboard import DashboardSummary
from app.schemas.report import ReportInfo, ReportResult
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService

router = APIRouter(tags=["Reports & Dashboard"])


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
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return service.run(report_key, user.company_id, start_date, end_date)
