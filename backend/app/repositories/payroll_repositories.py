from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    Employee,
    PayItem,
    Paycheck,
    PaycheckLine,
    PaySchedule,
    PayrollLiabilityPayment,
    PayrollRun,
    TimeEntry,
)
from app.models.enums import PayrollRunStatus
from app.repositories.base import BaseRepository


class PayScheduleRepository(BaseRepository):
    model = PaySchedule

    def order_by_columns(self) -> list:
        return [PaySchedule.name]


class PayItemRepository(BaseRepository):
    model = PayItem

    def order_by_columns(self) -> list:
        return [PayItem.kind, PayItem.name]

    def get_by_name(self, company_id: int, name: str) -> PayItem | None:
        query = select(PayItem).where(PayItem.company_id == company_id, func.lower(PayItem.name) == name.lower())
        return self.session.scalar(query)


class EmployeeRepository(BaseRepository):
    model = Employee

    def order_by_columns(self) -> list:
        return [Employee.display_name]


class PayrollRunRepository(BaseRepository):
    model = PayrollRun

    def order_by_columns(self) -> list:
        return [PayrollRun.pay_date.desc(), PayrollRun.id.desc()]

    def approved_between(self, company_id: int, start: date | None, end: date) -> list[PayrollRun]:
        query = select(PayrollRun).where(
            PayrollRun.company_id == company_id,
            PayrollRun.status == PayrollRunStatus.APPROVED,
            PayrollRun.pay_date <= end,
        )
        if start is not None:
            query = query.where(PayrollRun.pay_date >= start)
        return list(self.session.scalars(query.order_by(PayrollRun.pay_date)))

    def accrued_per_pay_item(self, company_id: int) -> dict[int, Decimal]:
        """Amounts on approved paychecks, per pay item."""
        query = (
            select(PaycheckLine.pay_item_id, func.sum(PaycheckLine.amount))
            .join(Paycheck, Paycheck.id == PaycheckLine.paycheck_id)
            .join(PayrollRun, PayrollRun.id == Paycheck.run_id)
            .where(
                PayrollRun.company_id == company_id,
                PayrollRun.status == PayrollRunStatus.APPROVED,
                PaycheckLine.pay_item_id.is_not(None),
            )
            .group_by(PaycheckLine.pay_item_id)
        )
        result = {}
        for pay_item_id, total in self.session.execute(query):
            result[pay_item_id] = Decimal(total)
        return result


class LiabilityPaymentRepository(BaseRepository):
    model = PayrollLiabilityPayment

    def order_by_columns(self) -> list:
        return [PayrollLiabilityPayment.payment_date.desc(), PayrollLiabilityPayment.id.desc()]

    def paid_per_pay_item(self, company_id: int) -> dict[int, Decimal]:
        query = (
            select(PayrollLiabilityPayment.pay_item_id, func.sum(PayrollLiabilityPayment.amount))
            .where(PayrollLiabilityPayment.company_id == company_id, PayrollLiabilityPayment.is_void.is_(False))
            .group_by(PayrollLiabilityPayment.pay_item_id)
        )
        result = {}
        for pay_item_id, total in self.session.execute(query):
            result[pay_item_id] = Decimal(total)
        return result


class TimeEntryRepository(BaseRepository):
    model = TimeEntry

    def order_by_columns(self) -> list:
        return [TimeEntry.work_date.desc(), TimeEntry.id.desc()]

    def list_filtered(
        self,
        company_id: int,
        start: date | None = None,
        end: date | None = None,
        employee_id: int | None = None,
        customer_id: int | None = None,
        unbilled_only: bool = False,
    ) -> list[TimeEntry]:
        query = select(TimeEntry).where(TimeEntry.company_id == company_id)
        if start is not None:
            query = query.where(TimeEntry.work_date >= start)
        if end is not None:
            query = query.where(TimeEntry.work_date <= end)
        if employee_id is not None:
            query = query.where(TimeEntry.employee_id == employee_id)
        if customer_id is not None:
            query = query.where(TimeEntry.customer_id == customer_id)
        if unbilled_only:
            query = query.where(TimeEntry.billable.is_(True), TimeEntry.invoice_id.is_(None))
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def hours_for(self, company_id: int, employee_id: int, start: date, end: date) -> Decimal:
        query = select(func.coalesce(func.sum(TimeEntry.hours), 0)).where(
            TimeEntry.company_id == company_id,
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date >= start,
            TimeEntry.work_date <= end,
        )
        return Decimal(self.session.scalar(query))

    def for_invoice(self, company_id: int, invoice_id: int) -> list[TimeEntry]:
        query = select(TimeEntry).where(TimeEntry.company_id == company_id, TimeEntry.invoice_id == invoice_id)
        return list(self.session.scalars(query))
