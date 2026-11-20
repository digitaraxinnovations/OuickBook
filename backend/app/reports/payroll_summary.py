"""Payroll Summary: gross pay, deductions, taxes and net pay per employee for paydays in a period."""

from datetime import date

from app.core.money import ZERO
from app.reports.base import Report
from app.repositories.payroll_repositories import PayrollRunRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow


class EmployeeTotals:
    def __init__(self, name: str):
        self.name = name
        self.gross = ZERO
        self.deductions = ZERO
        self.taxes = ZERO
        self.employer = ZERO


class PayrollSummaryReport(Report):
    key = "payroll-summary"
    group = "Employees"
    title = "Payroll Summary"
    description = "Gross pay, deductions, taxes and net pay per employee (approved payrolls)."

    def __init__(self, run_repository: PayrollRunRepository):
        self.run_repository = run_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        per_employee = {}
        for run in self.run_repository.approved_between(company_id, start_date, end_date):
            for paycheck in run.paychecks:
                totals = per_employee.get(paycheck.employee_id)
                if totals is None:
                    totals = EmployeeTotals(paycheck.employee.display_name)
                    per_employee[paycheck.employee_id] = totals
                totals.gross += paycheck.gross_pay
                totals.deductions += paycheck.employee_deductions
                totals.taxes += paycheck.employee_taxes
                totals.employer += paycheck.employer_cost

        sections = []
        total_gross = ZERO
        total_net = ZERO
        total_employer = ZERO
        for totals in sorted(per_employee.values(), key=lambda item: item.name):
            rows = [
                ReportRow(label="Gross pay", amount=totals.gross),
                ReportRow(label="Deductions", amount=-totals.deductions),
                ReportRow(label="Employee taxes", amount=-totals.taxes),
            ]
            section = self.make_section(f"{totals.name} - net pay", rows)
            sections.append(section)
            total_gross += totals.gross
            total_net += section.total
            total_employer += totals.employer

        summary = [
            ReportRow(label="Total gross pay", amount=total_gross),
            ReportRow(label="Total net pay", amount=total_net),
            ReportRow(label="Employer taxes and contributions", amount=total_employer),
            ReportRow(label="Total payroll cost", amount=total_gross + total_employer),
        ]
        return self.make_result(start_date, end_date, sections, summary)
