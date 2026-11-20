"""
Payroll runs: create a draft for a pay period, adjust paychecks, then approve.

Approving posts one journal entry for the whole run:
    Debit  wage expense            gross pay
    Debit  payroll tax expense     employer taxes and contributions
    Credit bank                    net pay
    Credit liability accounts      deductions, employee taxes, employer amounts
and gives each paper paycheck the next check number of the bank account.
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.pay_periods import next_period_end, period_start
from app.models import Account, Employee, PayItem, Paycheck, PayrollRun
from app.models.enums import AccountType, JournalSource, PayItemKind, PaycheckMethod, PayrollRunStatus, PayType
from app.repositories.account_repository import AccountRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.payroll_repositories import (
    EmployeeRepository,
    PayItemRepository,
    PayrollRunRepository,
    PayScheduleRepository,
    TimeEntryRepository,
)
from app.schemas.payroll import PaycheckUpdate, PayrollRunCreate
from app.seed.default_accounts import DetailType, SystemAccount
from app.services.base import BaseService
from app.services.check_numbers import CheckNumberService
from app.services.inventory_service import AccountTotals
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.paycheck_calculator import EMPLOYEE_SIDE, EMPLOYER_SIDE, PaycheckCalculator
from app.services.system_accounts import SystemAccounts

EARNING_KINDS = (PayItemKind.REGULAR, PayItemKind.OVERTIME, PayItemKind.SALARY, PayItemKind.EARNING)


class PayrollRunService(BaseService):
    def __init__(
        self,
        session,
        repository: PayrollRunRepository,
        schedule_repository: PayScheduleRepository,
        employee_repository: EmployeeRepository,
        item_repository: PayItemRepository,
        time_repository: TimeEntryRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        system_accounts: SystemAccounts,
        check_numbers: CheckNumberService,
        calculator: PaycheckCalculator,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.repository = repository
        self.schedule_repository = schedule_repository
        self.employee_repository = employee_repository
        self.item_repository = item_repository
        self.time_repository = time_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.system_accounts = system_accounts
        self.check_numbers = check_numbers
        self.calculator = calculator
        self.ledger = ledger

    # ---------- reading ----------

    def list(self, company_id: int) -> list[PayrollRun]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, run_id: int) -> PayrollRun:
        run = self.repository.get(company_id, run_id)
        if run is None:
            raise NotFoundError("Payroll run not found.")
        return run

    def get_draft(self, company_id: int, run_id: int) -> PayrollRun:
        run = self.get(company_id, run_id)
        if run.status != PayrollRunStatus.DRAFT:
            raise BusinessRuleError("This payroll has already been approved.")
        return run

    # ---------- creating a draft ----------

    def create(self, company_id: int, data: PayrollRunCreate) -> PayrollRun:
        schedule = None
        if data.pay_schedule_id is not None:
            schedule = self.schedule_repository.get(company_id, data.pay_schedule_id)
            if schedule is None:
                raise BusinessRuleError("That pay schedule does not exist.")

        period_end = data.period_end or (schedule.next_period_end if schedule else None)
        pay_date = data.pay_date or (schedule.next_pay_date if schedule else None)
        start = data.period_start or (period_start(schedule.frequency, period_end) if schedule and period_end else None)
        if period_end is None or pay_date is None or start is None:
            raise BusinessRuleError("Enter the pay period and the pay date.")
        if start > period_end:
            raise BusinessRuleError("The pay period start cannot be after its end.")

        bank = self.check_bank(company_id, data.bank_account_id)
        employees = self.choose_employees(company_id, schedule, data.employee_ids)

        run = PayrollRun(
            company_id=company_id,
            pay_schedule_id=schedule.id if schedule else None,
            period_start=start,
            period_end=period_end,
            pay_date=pay_date,
            bank_account_id=bank.id,
            status=PayrollRunStatus.DRAFT,
        )
        for employee in employees:
            paycheck = Paycheck(employee_id=employee.id, payment_method=employee.payment_method)
            hours = self.hours_for(company_id, employee, start, period_end)
            frequency = self.frequency_for(employee, schedule)
            self.calculator.fill(paycheck, employee, frequency, pay_date, hours, 0, None)
            run.paychecks.append(paycheck)
        self.repository.add(run)
        self.commit()
        return run

    def choose_employees(self, company_id: int, schedule, employee_ids: list[int]) -> list[Employee]:
        if employee_ids:
            employees = []
            for employee_id in employee_ids:
                employee = self.employee_repository.get(company_id, employee_id)
                if employee is None or not employee.is_active:
                    raise BusinessRuleError("Only active employees can be paid.")
                employees.append(employee)
            return employees

        employees = []
        for employee in self.employee_repository.list_all(company_id, active_only=True):
            if schedule is None or employee.pay_schedule_id == schedule.id:
                employees.append(employee)
        if not employees:
            raise BusinessRuleError("There are no active employees to pay.")
        return employees

    def hours_for(self, company_id: int, employee: Employee, start: date, end: date):
        """Hourly employees: hours from time entries, else their usual hours."""
        if employee.pay_type != PayType.HOURLY:
            return 0
        hours = self.time_repository.hours_for(company_id, employee.id, start, end)
        if hours > 0:
            return hours
        return employee.default_hours

    def frequency_for(self, employee: Employee, schedule) -> str | None:
        if employee.pay_schedule is not None:
            return employee.pay_schedule.frequency
        if schedule is not None:
            return schedule.frequency
        return None

    def check_bank(self, company_id: int, account_id: int) -> Account:
        account = self.account_repository.get(company_id, account_id)
        if account is None or not account.is_active or account.account_type != AccountType.ASSET or account.detail_type != DetailType.BANK:
            raise BusinessRuleError("Pay employees from a bank account.")
        return account

    # ---------- changing a draft ----------

    def update_paycheck(self, company_id: int, run_id: int, paycheck_id: int, data: PaycheckUpdate) -> PayrollRun:
        run = self.get_draft(company_id, run_id)
        paycheck = self.find_paycheck(run, paycheck_id)
        item_amounts = self.typed_items(company_id, data)
        schedule = self.schedule_repository.get(company_id, run.pay_schedule_id) if run.pay_schedule_id else None
        frequency = self.frequency_for(paycheck.employee, schedule)
        self.calculator.fill(paycheck, paycheck.employee, frequency, run.pay_date, data.regular_hours, data.overtime_hours, item_amounts)
        self.commit()
        return run

    def typed_items(self, company_id: int, data: PaycheckUpdate):
        """{pay_item_id: (item, amount)} typed by the user, or None to use the employee's usual items."""
        if data.use_usual_items:
            return None
        item_amounts = {}
        for item_input in data.items:
            item = self.item_repository.get(company_id, item_input.pay_item_id)
            if item is None:
                raise BusinessRuleError("That pay item does not exist.")
            item_amounts[item.id] = (item, item_input.amount)
        return item_amounts

    def remove_paycheck(self, company_id: int, run_id: int, paycheck_id: int) -> PayrollRun:
        run = self.get_draft(company_id, run_id)
        paycheck = self.find_paycheck(run, paycheck_id)
        if len(run.paychecks) == 1:
            raise BusinessRuleError("A payroll needs at least one paycheck. Delete the payroll instead.")
        run.paychecks.remove(paycheck)
        self.commit()
        return run

    def find_paycheck(self, run: PayrollRun, paycheck_id: int) -> Paycheck:
        for paycheck in run.paychecks:
            if paycheck.id == paycheck_id:
                return paycheck
        raise NotFoundError("Paycheck not found.")

    def delete_draft(self, company_id: int, run_id: int) -> None:
        run = self.get_draft(company_id, run_id)
        self.session.delete(run)
        self.commit()

    # ---------- approving and voiding ----------

    def approve(self, company_id: int, run_id: int) -> PayrollRun:
        run = self.get_draft(company_id, run_id)
        totals = AccountTotals()
        for paycheck in run.paychecks:
            for line in paycheck.lines:
                self.add_line_to_totals(company_id, line.kind, line.pay_item, line.amount, totals)
            totals.credit(run.bank_account_id, paycheck.net_pay)
            if paycheck.payment_method == PaycheckMethod.CHECK and paycheck.net_pay > 0:
                paycheck.check_number = self.check_numbers.assign(company_id, run.bank_account_id, None)

        ledger_lines = totals.ledger_lines()
        if len(ledger_lines) < 2:
            raise BusinessRuleError("There is nothing to pay in this payroll.")
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=run.pay_date,
            source_type=JournalSource.PAYROLL,
            source_id=run.id,
            memo=f"Payroll {run.period_start:%b %d} - {run.period_end:%b %d, %Y}",
            lines=ledger_lines,
        )
        run.journal_entry_id = entry.id
        run.status = PayrollRunStatus.APPROVED
        self.move_schedule_on(company_id, run)
        self.commit()
        return run

    def add_line_to_totals(self, company_id: int, kind: PayItemKind, item: PayItem | None, amount, totals: AccountTotals) -> None:
        if kind in EARNING_KINDS:
            totals.debit(self.expense_account_id(company_id, item, SystemAccount.WAGES), amount)
        elif kind in EMPLOYEE_SIDE:
            totals.credit(self.liability_account_id(company_id, item), amount)
        elif kind in EMPLOYER_SIDE:
            totals.debit(self.expense_account_id(company_id, item, SystemAccount.PAYROLL_TAXES), amount)
            totals.credit(self.liability_account_id(company_id, item), amount)

    def expense_account_id(self, company_id: int, item: PayItem | None, default_key: str) -> int:
        if item is not None and item.expense_account_id is not None:
            return item.expense_account_id
        return self.system_accounts.get(company_id, default_key).id

    def liability_account_id(self, company_id: int, item: PayItem | None) -> int:
        if item is not None and item.liability_account_id is not None:
            return item.liability_account_id
        return self.system_accounts.get(company_id, SystemAccount.PAYROLL_LIABILITIES).id

    def move_schedule_on(self, company_id: int, run: PayrollRun) -> None:
        """After paying the schedule's next period, its next period moves on by one."""
        if run.pay_schedule_id is None:
            return
        schedule = self.schedule_repository.get(company_id, run.pay_schedule_id)
        if run.period_end != schedule.next_period_end:
            return
        days_to_pay_date = (schedule.next_pay_date - schedule.next_period_end).days
        schedule.next_period_end = next_period_end(schedule.frequency, schedule.next_period_end)
        schedule.next_pay_date = date.fromordinal(schedule.next_period_end.toordinal() + days_to_pay_date)

    def void(self, company_id: int, run_id: int) -> PayrollRun:
        run = self.get(company_id, run_id)
        if run.status != PayrollRunStatus.APPROVED:
            raise BusinessRuleError("Only an approved payroll can be voided. Delete a draft instead.")
        original = self.journal_repository.get(company_id, run.journal_entry_id)
        self.ledger.reverse(company_id, original, date.today(), JournalSource.PAYROLL_VOID, "Void of payroll")
        run.status = PayrollRunStatus.VOID
        self.commit()
        return run
