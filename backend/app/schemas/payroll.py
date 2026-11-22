from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PayCalculation, PayFrequency, PayItemKind, PaycheckMethod, PayrollRunStatus, PayType
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel

# ---------- setup ----------


class PayScheduleWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    frequency: PayFrequency
    next_period_end: date
    next_pay_date: date
    is_active: bool = True


class PayScheduleRead(ORMModel):
    id: int
    name: str
    frequency: PayFrequency
    next_period_end: date
    next_pay_date: date
    next_period_start: date
    is_active: bool


class PayItemWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    kind: PayItemKind
    calculation: PayCalculation = PayCalculation.FIXED
    default_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=4)
    # Empty = Wages & Salaries / Payroll Taxes & Benefits.
    expense_account_id: int | None = None
    # Empty = Payroll Liabilities.
    liability_account_id: int | None = None
    is_active: bool = True


class PayItemRead(ORMModel):
    id: int
    name: str
    kind: PayItemKind
    calculation: PayCalculation
    default_amount: Decimal
    expense_account: AccountSummary | None
    liability_account: AccountSummary | None
    is_active: bool


class EmployeePayItemInput(BaseModel):
    pay_item_id: int
    # Money for FIXED items, a percent for PERCENT items.
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=4)


class EmployeeWrite(CleanStringsModel):
    display_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    tax_id: str | None = Field(default=None, max_length=50)
    hire_date: date | None = None
    release_date: date | None = None
    pay_schedule_id: int | None = None
    pay_type: PayType = PayType.HOURLY
    pay_rate: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    default_hours: Decimal = Field(default=Decimal("0"), ge=0, max_digits=8, decimal_places=2)
    payment_method: PaycheckMethod = PaycheckMethod.CHECK
    is_active: bool = True
    pay_items: list[EmployeePayItemInput] = Field(default_factory=list)


class EmployeePayItemRead(ORMModel):
    pay_item_id: int
    amount: Decimal


class EmployeeRead(ORMModel):
    id: int
    display_name: str
    email: str | None
    phone: str | None
    address: str | None
    tax_id: str | None
    hire_date: date | None
    release_date: date | None
    pay_schedule_id: int | None
    pay_type: PayType
    pay_rate: Decimal
    default_hours: Decimal
    payment_method: PaycheckMethod
    is_active: bool
    pay_items: list[EmployeePayItemRead]


# ---------- payroll runs ----------


class PayrollRunCreate(BaseModel):
    pay_schedule_id: int | None = None
    # Empty = the schedule's next period and pay date.
    period_start: date | None = None
    period_end: date | None = None
    pay_date: date | None = None
    bank_account_id: int
    # Empty = every active employee on the schedule (or every active employee).
    employee_ids: list[int] = Field(default_factory=list)


class PaycheckItemInput(BaseModel):
    pay_item_id: int
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class PaycheckUpdate(BaseModel):
    regular_hours: Decimal = Field(default=Decimal("0"), ge=0, max_digits=8, decimal_places=2)
    overtime_hours: Decimal = Field(default=Decimal("0"), ge=0, max_digits=8, decimal_places=2)
    # The money amount of each pay item on this paycheck.
    items: list[PaycheckItemInput] = Field(default_factory=list)
    # True = ignore `items` and work out the employee's usual pay items again
    # (e.g. after changing hours, so percentage taxes follow the new gross pay).
    use_usual_items: bool = False


class PaycheckLineRead(ORMModel):
    id: int
    pay_item_id: int | None
    kind: PayItemKind
    description: str
    hours: Decimal | None
    rate: Decimal | None
    amount: Decimal


class EmployeeSummary(ORMModel):
    id: int
    display_name: str
    pay_type: PayType


class PaycheckRead(ORMModel):
    id: int
    employee: EmployeeSummary
    regular_hours: Decimal
    overtime_hours: Decimal
    gross_pay: Decimal
    employee_deductions: Decimal
    employee_taxes: Decimal
    net_pay: Decimal
    employer_cost: Decimal
    payment_method: PaycheckMethod
    check_number: str | None
    deposit_reference: str | None = None
    lines: list[PaycheckLineRead]


class PayrollRunSummary(ORMModel):
    id: int
    period_start: date
    period_end: date
    pay_date: date
    status: PayrollRunStatus
    bank_account: AccountSummary
    total_gross: Decimal
    total_net: Decimal
    total_employer_cost: Decimal


class PayrollRunRead(PayrollRunSummary):
    pay_schedule_id: int | None
    paychecks: list[PaycheckRead]


# ---------- liabilities ----------


class LiabilityBalance(BaseModel):
    pay_item_id: int
    name: str
    kind: PayItemKind
    accrued: Decimal
    paid: Decimal
    balance: Decimal


class LiabilityPaymentCreate(CleanStringsModel):
    pay_item_id: int
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    bank_account_id: int
    memo: str | None = Field(default=None, max_length=500)


class LiabilityPaymentRead(ORMModel):
    id: int
    pay_item_id: int
    payment_date: date
    amount: Decimal
    bank_account: AccountSummary
    memo: str | None
    is_void: bool


# ---------- time ----------


class TimeEntryWrite(CleanStringsModel):
    employee_id: int | None = None
    vendor_id: int | None = None
    work_date: date
    hours: Decimal = Field(gt=0, le=24, max_digits=8, decimal_places=2)
    customer_id: int | None = None
    project_id: int | None = None
    product_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    billable: bool = False
    bill_rate: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class TimeEntryRead(ORMModel):
    id: int
    employee_id: int | None
    vendor_id: int | None
    work_date: date
    hours: Decimal
    customer_id: int | None
    project_id: int | None
    product_id: int | None
    description: str | None
    billable: bool
    bill_rate: Decimal | None
    invoice_id: int | None
