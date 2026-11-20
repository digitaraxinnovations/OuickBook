"""
Works out one paycheck.

1. Earnings
   - Hourly:  regular hours x rate, overtime hours x rate x overtime multiplier
   - Salary:  yearly salary / pay periods per year
   - Extra earning items (bonus, commission...)
   = gross pay
2. Deductions and employee taxes come off gross pay  -> net pay
3. Employer taxes and contributions are an extra cost to the company
   (they do not change net pay)

PERCENT items are a percentage of gross pay (earning items: of base pay).
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.core.pay_periods import PERIODS_PER_YEAR
from app.integrations.payroll import PayrollProvider
from app.models import Employee, PayItem, Paycheck, PaycheckLine
from app.models.enums import PayCalculation, PayItemKind, PayType

EMPLOYEE_SIDE = (PayItemKind.DEDUCTION, PayItemKind.EMPLOYEE_TAX)
EMPLOYER_SIDE = (PayItemKind.EMPLOYER_TAX, PayItemKind.EMPLOYER_CONTRIBUTION)


class PaycheckCalculator:
    def __init__(self, provider: PayrollProvider, overtime_multiplier: Decimal):
        self.provider = provider
        self.overtime_multiplier = overtime_multiplier

    def fill(
        self,
        paycheck: Paycheck,
        employee: Employee,
        frequency: str | None,
        pay_date: date,
        regular_hours: Decimal,
        overtime_hours: Decimal,
        item_amounts: dict[int, tuple[PayItem, Decimal]] | None,
    ) -> None:
        """
        Replace the paycheck's lines and totals.

        `item_amounts` - {pay_item_id: (pay item, money amount)} typed by the user.
        When None, the employee's usual pay items are used.
        """
        paycheck.lines.clear()
        paycheck.regular_hours = regular_hours if employee.pay_type == PayType.HOURLY else ZERO
        paycheck.overtime_hours = overtime_hours if employee.pay_type == PayType.HOURLY else ZERO

        base_pay = self.add_base_pay(paycheck, employee, frequency)
        items = self.items_for(employee, item_amounts)

        gross = base_pay
        for item, value in items:
            if item.kind == PayItemKind.EARNING:
                amount = self.amount_of(item, value, base_pay, item_amounts is not None)
                gross += amount
                self.add_line(paycheck, item, item.name, amount)

        deductions = ZERO
        taxes = ZERO
        employer = ZERO
        for item, value in items:
            if item.kind == PayItemKind.EARNING:
                continue
            amount = self.amount_of(item, value, gross, item_amounts is not None)
            if item.kind == PayItemKind.DEDUCTION:
                deductions += amount
            elif item.kind == PayItemKind.EMPLOYEE_TAX:
                taxes += amount
            else:
                employer += amount
            self.add_line(paycheck, item, item.name, amount)

        for tax in self.provider.calculate_taxes(employee.id, gross, pay_date):
            # A connected provider's taxes would be added here (see integrations/payroll.py).
            raise BusinessRuleError(f"Map the provider tax '{tax.name}' to a pay item first.")

        net = gross - deductions - taxes
        if net < 0:
            raise BusinessRuleError(f"{employee.display_name}'s deductions and taxes are more than their gross pay.")

        paycheck.gross_pay = gross
        paycheck.employee_deductions = deductions
        paycheck.employee_taxes = taxes
        paycheck.employer_cost = employer
        paycheck.net_pay = net

    def add_base_pay(self, paycheck: Paycheck, employee: Employee, frequency: str | None) -> Decimal:
        if employee.pay_type == PayType.SALARY:
            if frequency is None:
                raise BusinessRuleError(f"Give {employee.display_name} a pay schedule so their salary can be split into paychecks.")
            amount = to_money(employee.pay_rate / PERIODS_PER_YEAR[frequency])
            paycheck.lines.append(
                PaycheckLine(kind=PayItemKind.SALARY, description="Salary", hours=None, rate=None, amount=amount)
            )
            return amount

        total = ZERO
        if paycheck.regular_hours > 0:
            amount = to_money(paycheck.regular_hours * employee.pay_rate)
            paycheck.lines.append(
                PaycheckLine(
                    kind=PayItemKind.REGULAR,
                    description="Regular pay",
                    hours=paycheck.regular_hours,
                    rate=employee.pay_rate,
                    amount=amount,
                )
            )
            total += amount
        if paycheck.overtime_hours > 0:
            rate = employee.pay_rate * self.overtime_multiplier
            amount = to_money(paycheck.overtime_hours * rate)
            paycheck.lines.append(
                PaycheckLine(
                    kind=PayItemKind.OVERTIME,
                    description="Overtime pay",
                    hours=paycheck.overtime_hours,
                    rate=rate,
                    amount=amount,
                )
            )
            total += amount
        return total

    def items_for(self, employee: Employee, item_amounts) -> list[tuple[PayItem, Decimal]]:
        """(pay item, value) pairs: typed money amounts, or the employee's usual amounts/percents."""
        if item_amounts is not None:
            return list(item_amounts.values())
        result = []
        for assigned in employee.pay_items:
            if assigned.pay_item.is_active:
                result.append((assigned.pay_item, assigned.amount))
        return result

    def amount_of(self, item: PayItem, value: Decimal, base: Decimal, is_typed_money: bool) -> Decimal:
        if is_typed_money or item.calculation == PayCalculation.FIXED:
            return to_money(value)
        return to_money(base * value / Decimal("100"))

    def add_line(self, paycheck: Paycheck, item: PayItem, description: str, amount: Decimal) -> None:
        if amount == 0:
            return
        paycheck.lines.append(
            PaycheckLine(pay_item_id=item.id, kind=item.kind, description=description, hours=None, rate=None, amount=amount)
        )
