"""Employees, pay schedules, pay items, payroll runs, liabilities and time."""

from datetime import date

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    get_company_repository,
    get_current_user,
    get_payroll_liability_service,
    get_payroll_provider,
    get_payroll_run_service,
    get_payroll_setup_service,
    get_time_service,
)
from app.api.responses import pdf_response
from app.documents.pay_stub import pay_stub_document
from app.documents.pdf_builder import DocumentPdfBuilder
from app.integrations.payroll import PayrollProvider
from app.models import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.payroll import (
    EmployeeRead,
    EmployeeWrite,
    LiabilityBalance,
    LiabilityPaymentCreate,
    LiabilityPaymentRead,
    PaycheckUpdate,
    PayItemRead,
    PayItemWrite,
    PayrollRunCreate,
    PayrollRunRead,
    PayrollRunSummary,
    PayScheduleRead,
    PayScheduleWrite,
    TimeEntryRead,
    TimeEntryWrite,
)
from app.services.customer_documents_service import PdfFile
from app.services.payroll_liability_service import PayrollLiabilityService
from app.services.payroll_run_service import PayrollRunService
from app.services.payroll_setup_service import PayrollSetupService
from app.services.time_service import TimeService

router = APIRouter(tags=["Payroll and time"])

SetupService = Depends(get_payroll_setup_service)
RunService = Depends(get_payroll_run_service)
LiabilityService = Depends(get_payroll_liability_service)
Time = Depends(get_time_service)
CurrentUser = Depends(get_current_user)


# ---------- pay schedules ----------

@router.get("/pay-schedules", response_model=list[PayScheduleRead])
def list_schedules(user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.list_schedules(user.company_id)


@router.post("/pay-schedules", response_model=PayScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(data: PayScheduleWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_schedule(user.company_id, data)


@router.put("/pay-schedules/{schedule_id}", response_model=PayScheduleRead)
def update_schedule(schedule_id: int, data: PayScheduleWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_schedule(user.company_id, data, schedule_id)


# ---------- pay items ----------

@router.get("/pay-items", response_model=list[PayItemRead])
def list_pay_items(user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.list_items(user.company_id)


@router.post("/pay-items", response_model=PayItemRead, status_code=status.HTTP_201_CREATED)
def create_pay_item(data: PayItemWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_item(user.company_id, data)


@router.put("/pay-items/{item_id}", response_model=PayItemRead)
def update_pay_item(item_id: int, data: PayItemWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_item(user.company_id, data, item_id)


# ---------- employees ----------

@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(active_only: bool = False, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.list_employees(user.company_id, active_only)


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(employee_id: int, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.get_employee(user.company_id, employee_id)


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(data: EmployeeWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_employee(user.company_id, data)


@router.put("/employees/{employee_id}", response_model=EmployeeRead)
def update_employee(employee_id: int, data: EmployeeWrite, user: User = CurrentUser, service: PayrollSetupService = SetupService):
    return service.save_employee(user.company_id, data, employee_id)


# ---------- payroll runs ----------

@router.get("/payroll-runs", response_model=list[PayrollRunSummary])
def list_runs(user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.list(user.company_id)


@router.get("/payroll-runs/{run_id}", response_model=PayrollRunRead)
def get_run(run_id: int, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.get(user.company_id, run_id)


@router.post("/payroll-runs", response_model=PayrollRunRead, status_code=status.HTTP_201_CREATED)
def create_run(data: PayrollRunCreate, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.create(user.company_id, data)


@router.put("/payroll-runs/{run_id}/paychecks/{paycheck_id}", response_model=PayrollRunRead)
def update_paycheck(run_id: int, paycheck_id: int, data: PaycheckUpdate, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.update_paycheck(user.company_id, run_id, paycheck_id, data)


@router.delete("/payroll-runs/{run_id}/paychecks/{paycheck_id}", response_model=PayrollRunRead)
def remove_paycheck(run_id: int, paycheck_id: int, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.remove_paycheck(user.company_id, run_id, paycheck_id)


@router.post("/payroll-runs/{run_id}/approve", response_model=PayrollRunRead)
def approve_run(run_id: int, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.approve(user.company_id, run_id)


@router.post("/payroll-runs/{run_id}/void", response_model=PayrollRunRead)
def void_run(run_id: int, user: User = CurrentUser, service: PayrollRunService = RunService):
    return service.void(user.company_id, run_id)


@router.delete("/payroll-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: int, user: User = CurrentUser, service: PayrollRunService = RunService):
    service.delete_draft(user.company_id, run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/payroll-runs/{run_id}/paychecks/{paycheck_id}/stub")
def pay_stub(
    run_id: int,
    paycheck_id: int,
    user: User = CurrentUser,
    service: PayrollRunService = RunService,
    companies: CompanyRepository = Depends(get_company_repository),
):
    run = service.get(user.company_id, run_id)
    paycheck = service.find_paycheck(run, paycheck_id)
    company = companies.get(user.company_id)
    content = DocumentPdfBuilder(company).build(pay_stub_document(paycheck, company))
    filename = f"Pay-stub-{paycheck.employee.display_name}-{run.pay_date}.pdf".replace(" ", "-")
    return pdf_response(PdfFile(filename, content))


# ---------- liabilities ----------

@router.get("/payroll-liabilities", response_model=list[LiabilityBalance])
def liability_balances(user: User = CurrentUser, service: PayrollLiabilityService = LiabilityService):
    return service.balances(user.company_id)


@router.get("/payroll-liabilities/payments", response_model=list[LiabilityPaymentRead])
def liability_payments(user: User = CurrentUser, service: PayrollLiabilityService = LiabilityService):
    return service.list_payments(user.company_id)


@router.post("/payroll-liabilities/payments", response_model=LiabilityPaymentRead, status_code=status.HTTP_201_CREATED)
def pay_liability(data: LiabilityPaymentCreate, user: User = CurrentUser, service: PayrollLiabilityService = LiabilityService):
    return service.pay(user.company_id, data)


@router.post("/payroll-liabilities/payments/{payment_id}/void", response_model=LiabilityPaymentRead)
def void_liability_payment(payment_id: int, user: User = CurrentUser, service: PayrollLiabilityService = LiabilityService):
    return service.void_payment(user.company_id, payment_id)


@router.get("/payroll/provider")
def payroll_provider_status(user: User = CurrentUser, provider: PayrollProvider = Depends(get_payroll_provider)):
    return {"enabled": provider.is_enabled(), "provider": provider.provider_name}


# ---------- time ----------

@router.get("/time-entries", response_model=list[TimeEntryRead])
def list_time(
    start_date: date | None = None,
    end_date: date | None = None,
    employee_id: int | None = None,
    customer_id: int | None = None,
    unbilled_only: bool = False,
    user: User = CurrentUser,
    service: TimeService = Time,
):
    return service.list(user.company_id, start_date, end_date, employee_id, customer_id, unbilled_only)


@router.post("/time-entries", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
def create_time(data: TimeEntryWrite, user: User = CurrentUser, service: TimeService = Time):
    return service.save(user.company_id, data)


@router.put("/time-entries/{entry_id}", response_model=TimeEntryRead)
def update_time(entry_id: int, data: TimeEntryWrite, user: User = CurrentUser, service: TimeService = Time):
    return service.save(user.company_id, data, entry_id)


@router.delete("/time-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time(entry_id: int, user: User = CurrentUser, service: TimeService = Time):
    service.delete(user.company_id, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
