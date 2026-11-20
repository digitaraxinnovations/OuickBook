"""
Payroll.

- PaySchedule:   how often employees are paid (weekly, every two weeks...).
- Employee:      someone you pay through payroll (hourly or salary).
- PayItem:       anything on a paycheck besides regular and overtime pay:
                 extra earnings (bonus), deductions (401k), employee taxes,
                 employer taxes and employer contributions.
- EmployeePayItem: a pay item that goes on every paycheck of one employee.
- PayrollRun:    one pay day for a group of employees. Draft until approved;
                 approving posts the journal entry and numbers the checks.
- Paycheck / PaycheckLine: one employee's pay in a run.
- PayrollLiabilityPayment: money sent to pay withheld deductions and taxes.

Approving a run posts:
    Debit  wage expense (gross pay) and employer tax/benefit expense
    Credit the bank (net pay)
    Credit each pay item's liability account (withheld and employer amounts)
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.pay_periods import period_start
from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.contact import Vendor
from app.models.enums import (
    PayCalculation,
    PayFrequency,
    PayItemKind,
    PaycheckMethod,
    PayrollRunStatus,
    PayType,
)


class PaySchedule(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "pay_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[PayFrequency] = mapped_column(Enum(PayFrequency, native_enum=False, length=20))
    # The last day of the next pay period, and the pay day for it.
    next_period_end: Mapped[date] = mapped_column(Date)
    next_pay_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)

    @property
    def next_period_start(self) -> date:
        return period_start(self.frequency, self.next_period_end)


class Employee(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    # Social security number or other tax ID (for year-end forms).
    tax_id: Mapped[str | None] = mapped_column(String(50))
    hire_date: Mapped[date | None] = mapped_column(Date)
    release_date: Mapped[date | None] = mapped_column(Date)
    pay_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("pay_schedules.id"))
    pay_type: Mapped[PayType] = mapped_column(Enum(PayType, native_enum=False, length=20))
    # Hourly: rate per hour. Salary: amount per year.
    pay_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Hourly employees: hours used for a pay period when no time was entered.
    default_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    payment_method: Mapped[PaycheckMethod] = mapped_column(Enum(PaycheckMethod, native_enum=False, length=20))
    is_active: Mapped[bool] = mapped_column(default=True)

    pay_schedule: Mapped[PaySchedule | None] = relationship()
    pay_items: Mapped[list["EmployeePayItem"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="EmployeePayItem.id",
    )


class PayItem(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "pay_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[PayItemKind] = mapped_column(Enum(PayItemKind, native_enum=False, length=30))
    calculation: Mapped[PayCalculation] = mapped_column(Enum(PayCalculation, native_enum=False, length=20))
    # FIXED: an amount per paycheck. PERCENT: a percentage of gross pay.
    default_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    # Earnings and employer items are an expense of the company.
    expense_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    # Deductions, taxes and employer items are owed to someone until paid.
    liability_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    expense_account: Mapped[Account | None] = relationship(foreign_keys=[expense_account_id])
    liability_account: Mapped[Account | None] = relationship(foreign_keys=[liability_account_id])


class EmployeePayItem(Base):
    __tablename__ = "employee_pay_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    pay_item_id: Mapped[int] = mapped_column(ForeignKey("pay_items.id"))
    # Overrides the pay item's default amount / percent for this employee.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    employee: Mapped[Employee] = relationship(back_populates="pay_items")
    pay_item: Mapped[PayItem] = relationship()


class PayrollRun(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    pay_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("pay_schedules.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    pay_date: Mapped[date] = mapped_column(Date)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    status: Mapped[PayrollRunStatus] = mapped_column(Enum(PayrollRunStatus, native_enum=False, length=20))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))

    bank_account: Mapped[Account] = relationship()
    paychecks: Mapped[list["Paycheck"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Paycheck.id",
    )

    @property
    def total_gross(self) -> Decimal:
        return sum((paycheck.gross_pay for paycheck in self.paychecks), Decimal("0.00"))

    @property
    def total_net(self) -> Decimal:
        return sum((paycheck.net_pay for paycheck in self.paychecks), Decimal("0.00"))

    @property
    def total_employer_cost(self) -> Decimal:
        return sum((paycheck.employer_cost for paycheck in self.paychecks), Decimal("0.00"))


class Paycheck(Base):
    __tablename__ = "paychecks"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    regular_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    employee_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    employee_taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    employer_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[PaycheckMethod] = mapped_column(Enum(PaycheckMethod, native_enum=False, length=20))
    check_number: Mapped[str | None] = mapped_column(String(20))

    run: Mapped[PayrollRun] = relationship(back_populates="paychecks")
    employee: Mapped[Employee] = relationship()
    lines: Mapped[list["PaycheckLine"]] = relationship(
        back_populates="paycheck",
        cascade="all, delete-orphan",
        order_by="PaycheckLine.id",
    )


class PaycheckLine(Base):
    __tablename__ = "paycheck_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    paycheck_id: Mapped[int] = mapped_column(ForeignKey("paychecks.id"), index=True)
    # Empty for regular, overtime and salary pay.
    pay_item_id: Mapped[int | None] = mapped_column(ForeignKey("pay_items.id"))
    kind: Mapped[PayItemKind] = mapped_column(Enum(PayItemKind, native_enum=False, length=30))
    description: Mapped[str] = mapped_column(String(200))
    hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    paycheck: Mapped[Paycheck] = relationship(back_populates="lines")
    pay_item: Mapped[PayItem | None] = relationship()


class PayrollLiabilityPayment(CompanyOwnedMixin, TimestampMixin, Base):
    """Debit the pay item's liability account, Credit the bank."""

    __tablename__ = "payroll_liability_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    pay_item_id: Mapped[int] = mapped_column(ForeignKey("pay_items.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    memo: Mapped[str | None] = mapped_column(String(500))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    is_void: Mapped[bool] = mapped_column(default=False)

    pay_item: Mapped[PayItem] = relationship()
    bank_account: Mapped[Account] = relationship()


class TimeEntry(CompanyOwnedMixin, TimestampMixin, Base):
    """
    Hours worked by an employee (or a contractor vendor), optionally for a
    customer. Billable time can be added to the customer's invoice; an
    hourly employee's time also fills in their paycheck hours.
    """

    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    # The service done (fills in the invoice line).
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str | None] = mapped_column(String(500))
    billable: Mapped[bool] = mapped_column(default=False)
    # Price per hour charged to the customer.
    bill_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # Set once the time is on an invoice.
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))

    employee: Mapped[Employee | None] = relationship()
    vendor: Mapped[Vendor | None] = relationship()

    @property
    def worker_name(self) -> str:
        if self.employee is not None:
            return self.employee.display_name
        if self.vendor is not None:
            return self.vendor.display_name
        return ""
