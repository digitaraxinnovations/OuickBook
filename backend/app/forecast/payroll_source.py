"""
Expected pay days.

A draft payroll uses its own figures. Later pay days repeat the last
approved payroll of the schedule, or an estimate from the employees' rates.
The amount is gross pay plus employer costs (everything the pay run will
eventually cost, including taxes paid over later).
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.money import ZERO, to_money
from app.core.pay_periods import PERIODS_PER_YEAR, next_period_end
from app.forecast.base import CashSource
from app.models import PayrollRun, PaySchedule
from app.models.enums import PayrollRunStatus, PayType
from app.repositories.payroll_repositories import EmployeeRepository, PayrollRunRepository, PayScheduleRepository


def run_cost(run: PayrollRun) -> Decimal:
    return run.total_gross + run.total_employer_cost


class PayrollSource(CashSource):
    label = "Payroll"

    def __init__(self, schedules: PayScheduleRepository, runs: PayrollRunRepository, employees: EmployeeRepository):
        self.schedules = schedules
        self.runs = runs
        self.employees = employees

    def items(self, company_id, today: date, end: date):
        runs = self.runs.list_all(company_id)  # newest first
        result = []
        drafted = set()
        for run in runs:
            if run.status != PayrollRunStatus.DRAFT:
                continue
            drafted.add((run.pay_schedule_id, run.period_end))
            expected = max(run.pay_date, today)
            if expected <= end and run_cost(run) > 0:
                result.append(self.item(expected, -run_cost(run), "Draft payroll", link=f"/payroll/runs/{run.id}"))

        for schedule in self.schedules.list_all(company_id, active_only=True):
            amount = self.typical_cost(company_id, schedule, runs)
            if amount <= 0:
                continue
            for period_end, pay_date in self.pay_days(schedule, today, end):
                if (schedule.id, period_end) in drafted:
                    continue
                description = f"{schedule.name} (estimate)"
                result.append(self.item(max(pay_date, today), -amount, description, link="/payroll/runs"))
        return result

    def pay_days(self, schedule: PaySchedule, today: date, end: date) -> list[tuple[date, date]]:
        """(period end, pay date) from the next pay day up to `end`."""
        offset = timedelta(days=(schedule.next_pay_date - schedule.next_period_end).days)
        period_end = schedule.next_period_end
        result = []
        first = True
        while period_end + offset <= end:
            pay_date = period_end + offset
            # A missed next pay day is still owed; older gaps are not guessed.
            if first or pay_date >= today:
                result.append((period_end, pay_date))
            first = False
            period_end = next_period_end(schedule.frequency, period_end)
        return result

    def typical_cost(self, company_id: int, schedule: PaySchedule, runs: list[PayrollRun]) -> Decimal:
        for run in runs:
            if run.status == PayrollRunStatus.APPROVED and run.pay_schedule_id == schedule.id:
                return run_cost(run)
        total = ZERO
        for employee in self.employees.list_all(company_id, active_only=True):
            if employee.pay_schedule_id != schedule.id:
                continue
            if employee.pay_type == PayType.SALARY:
                total += to_money(employee.pay_rate / PERIODS_PER_YEAR[schedule.frequency])
            else:
                total += to_money(employee.pay_rate * employee.default_hours)
        return total
