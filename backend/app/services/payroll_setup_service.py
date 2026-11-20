"""Pay schedules, pay items and employees."""

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Employee, EmployeePayItem, PayItem, PaySchedule
from app.models.enums import AccountType, PayItemKind
from app.repositories.account_repository import AccountRepository
from app.repositories.payroll_repositories import EmployeeRepository, PayItemRepository, PayScheduleRepository
from app.schemas.payroll import EmployeeWrite, PayItemWrite, PayScheduleWrite
from app.services.base import BaseService

# Kinds the user can add (regular, overtime and salary pay are built in).
ADDABLE_KINDS = (
    PayItemKind.EARNING,
    PayItemKind.DEDUCTION,
    PayItemKind.EMPLOYEE_TAX,
    PayItemKind.EMPLOYER_TAX,
    PayItemKind.EMPLOYER_CONTRIBUTION,
)


class PayrollSetupService(BaseService):
    def __init__(
        self,
        session,
        schedule_repository: PayScheduleRepository,
        item_repository: PayItemRepository,
        employee_repository: EmployeeRepository,
        account_repository: AccountRepository,
    ):
        super().__init__(session)
        self.schedule_repository = schedule_repository
        self.item_repository = item_repository
        self.employee_repository = employee_repository
        self.account_repository = account_repository

    # ---------- pay schedules ----------

    def list_schedules(self, company_id: int) -> list[PaySchedule]:
        return self.schedule_repository.list_all(company_id)

    def get_schedule(self, company_id: int, schedule_id: int) -> PaySchedule:
        schedule = self.schedule_repository.get(company_id, schedule_id)
        if schedule is None:
            raise NotFoundError("Pay schedule not found.")
        return schedule

    def save_schedule(self, company_id: int, data: PayScheduleWrite, schedule_id: int | None = None) -> PaySchedule:
        if data.next_pay_date < data.next_period_end:
            raise BusinessRuleError("The pay date cannot be before the end of the pay period.")
        if schedule_id is None:
            schedule = PaySchedule(company_id=company_id)
        else:
            schedule = self.get_schedule(company_id, schedule_id)
        for field_name, value in data.model_dump().items():
            setattr(schedule, field_name, value)
        if schedule_id is None:
            self.schedule_repository.add(schedule)
        self.commit()
        return schedule

    # ---------- pay items ----------

    def list_items(self, company_id: int) -> list[PayItem]:
        return self.item_repository.list_all(company_id)

    def get_item(self, company_id: int, item_id: int) -> PayItem:
        item = self.item_repository.get(company_id, item_id)
        if item is None:
            raise NotFoundError("Pay item not found.")
        return item

    def save_item(self, company_id: int, data: PayItemWrite, item_id: int | None = None) -> PayItem:
        if data.kind not in ADDABLE_KINDS:
            raise BusinessRuleError("Regular, overtime and salary pay are built in.")
        existing = self.item_repository.get_by_name(company_id, data.name)
        if existing is not None and existing.id != item_id:
            raise ConflictError("A pay item with this name already exists.")
        self.check_account(company_id, data.expense_account_id, AccountType.EXPENSE, "an expense account")
        self.check_account(company_id, data.liability_account_id, AccountType.LIABILITY, "a liability account")

        if item_id is None:
            item = PayItem(company_id=company_id)
        else:
            item = self.get_item(company_id, item_id)
            if item.kind != data.kind:
                raise BusinessRuleError("The kind of a pay item cannot change. Add a new pay item instead.")
        for field_name, value in data.model_dump().items():
            setattr(item, field_name, value)
        if item_id is None:
            self.item_repository.add(item)
        self.commit()
        return item

    def check_account(self, company_id: int, account_id: int | None, account_type: AccountType, what: str) -> None:
        if account_id is None:
            return
        account = self.account_repository.get(company_id, account_id)
        if account is None or account.account_type != account_type:
            raise BusinessRuleError(f"Please choose {what}.")

    # ---------- employees ----------

    def list_employees(self, company_id: int, active_only: bool = False) -> list[Employee]:
        return self.employee_repository.list_all(company_id, active_only)

    def get_employee(self, company_id: int, employee_id: int) -> Employee:
        employee = self.employee_repository.get(company_id, employee_id)
        if employee is None:
            raise NotFoundError("Employee not found.")
        return employee

    def save_employee(self, company_id: int, data: EmployeeWrite, employee_id: int | None = None) -> Employee:
        if data.pay_schedule_id is not None:
            self.get_schedule(company_id, data.pay_schedule_id)
        if data.hire_date and data.release_date and data.release_date < data.hire_date:
            raise BusinessRuleError("The release date cannot be before the hire date.")

        if employee_id is None:
            employee = Employee(company_id=company_id)
        else:
            employee = self.get_employee(company_id, employee_id)

        for field_name, value in data.model_dump(exclude={"pay_items"}).items():
            setattr(employee, field_name, value)

        employee.pay_items.clear()
        self.session.flush()
        seen = set()
        for item_input in data.pay_items:
            item = self.get_item(company_id, item_input.pay_item_id)
            if item.id in seen:
                raise BusinessRuleError(f"{item.name} is on the employee twice.")
            seen.add(item.id)
            employee.pay_items.append(EmployeePayItem(pay_item_id=item.id, amount=item_input.amount))

        if employee_id is None:
            self.employee_repository.add(employee)
        self.commit()
        return employee
