"""
Budgets: a planned amount per income / expense account per month for one
year, optionally for one class or location.

Budget vs Actual compares the plan with what was posted in the same months
(and the same class / location).
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.dates import add_months
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import Budget, BudgetLine
from app.models.enums import AccountType
from app.repositories.account_repository import AccountRepository
from app.repositories.tracking_repositories import BudgetRepository, DimensionQueries, LocationRepository, TrackingClassRepository
from app.schemas.tracking import BudgetLineRead, BudgetRead, BudgetVsActual, BudgetVsActualRow, BudgetWrite
from app.services.base import BaseService

BUDGET_TYPES = (AccountType.INCOME, AccountType.EXPENSE)


class BudgetService(BaseService):
    def __init__(
        self,
        session,
        repository: BudgetRepository,
        account_repository: AccountRepository,
        class_repository: TrackingClassRepository,
        location_repository: LocationRepository,
        queries: DimensionQueries,
    ):
        super().__init__(session)
        self.repository = repository
        self.account_repository = account_repository
        self.class_repository = class_repository
        self.location_repository = location_repository
        self.queries = queries

    def list(self, company_id: int) -> list[Budget]:
        return self.repository.list_all(company_id)

    def get_record(self, company_id: int, budget_id: int) -> Budget:
        budget = self.repository.get(company_id, budget_id)
        if budget is None:
            raise NotFoundError("Budget not found.")
        return budget

    def get(self, company_id: int, budget_id: int) -> BudgetRead:
        return self.to_read(self.get_record(company_id, budget_id))

    def save(self, company_id: int, data: BudgetWrite, budget_id: int | None = None) -> BudgetRead:
        if data.class_id is not None and self.class_repository.get(company_id, data.class_id) is None:
            raise BusinessRuleError("That class does not exist.")
        if data.location_id is not None and self.location_repository.get(company_id, data.location_id) is None:
            raise BusinessRuleError("That location does not exist.")

        if budget_id is None:
            budget = Budget(company_id=company_id)
        else:
            budget = self.get_record(company_id, budget_id)
        budget.name = data.name
        budget.fiscal_year = data.fiscal_year
        budget.class_id = data.class_id
        budget.location_id = data.location_id

        budget.lines.clear()
        self.session.flush()
        seen = set()
        for line in data.lines:
            account = self.account_repository.get(company_id, line.account_id)
            if account is None or account.account_type not in BUDGET_TYPES:
                raise BusinessRuleError("Budgets are for income and expense accounts.")
            if account.id in seen:
                raise BusinessRuleError(f"{account.name} is in the budget twice.")
            seen.add(account.id)
            for month_index, amount in enumerate(line.months):
                if amount != 0:
                    budget.lines.append(BudgetLine(account_id=account.id, month=month_index + 1, amount=to_money(amount)))

        if budget_id is None:
            self.repository.add(budget)
        self.commit()
        return self.to_read(budget)

    def delete(self, company_id: int, budget_id: int) -> None:
        self.session.delete(self.get_record(company_id, budget_id))
        self.commit()

    def to_read(self, budget: Budget) -> BudgetRead:
        """Budget lines grouped back into one row of 12 months per account."""
        rows = {}
        for line in budget.lines:
            if line.account_id not in rows:
                rows[line.account_id] = BudgetLineRead(
                    account_id=line.account_id,
                    account_name=line.account.name,
                    account_type=line.account.account_type.value,
                    months=[ZERO] * 12,
                )
            rows[line.account_id].months[line.month - 1] = line.amount
        return BudgetRead(
            id=budget.id,
            name=budget.name,
            fiscal_year=budget.fiscal_year,
            class_id=budget.class_id,
            location_id=budget.location_id,
            lines=list(rows.values()),
        )

    # ---------- budget vs actual ----------

    def vs_actual(self, company_id: int, budget_id: int, first_month: int = 1, last_month: int = 12) -> BudgetVsActual:
        if not 1 <= first_month <= last_month <= 12:
            raise BusinessRuleError("Choose months between January and December.")
        budget = self.get_record(company_id, budget_id)
        start = date(budget.fiscal_year, first_month, 1)
        end = add_months(date(budget.fiscal_year, last_month, 1), 1) - timedelta(days=1)

        planned = {}
        for line in budget.lines:
            if first_month <= line.month <= last_month:
                planned[line.account_id] = planned.get(line.account_id, ZERO) + line.amount

        actual = self.actual_per_account(company_id, budget, start, end)

        rows = []
        budget_net = ZERO
        actual_net = ZERO
        account_ids = set(planned) | set(actual)
        for account in self.account_repository.list_all(company_id):
            if account.id not in account_ids or account.account_type not in BUDGET_TYPES:
                continue
            budget_amount = planned.get(account.id, ZERO)
            actual_amount = actual.get(account.id, ZERO)
            percent = None
            if budget_amount != 0:
                percent = to_money(actual_amount * Decimal("100") / budget_amount)
            rows.append(
                BudgetVsActualRow(
                    account_id=account.id,
                    account_name=account.name,
                    account_type=account.account_type.value,
                    budget=budget_amount,
                    actual=actual_amount,
                    difference=actual_amount - budget_amount,
                    percent_of_budget=percent,
                )
            )
            sign = Decimal("1") if account.account_type == AccountType.INCOME else Decimal("-1")
            budget_net += sign * budget_amount
            actual_net += sign * actual_amount

        rows.sort(key=lambda row: (row.account_type != "INCOME", row.account_name))
        return BudgetVsActual(
            budget_id=budget.id,
            name=budget.name,
            start_date=start,
            end_date=end,
            rows=rows,
            budget_net_income=budget_net,
            actual_net_income=actual_net,
        )

    def actual_per_account(self, company_id: int, budget: Budget, start: date, end: date) -> dict[int, Decimal]:
        """Income: credits - debits. Expenses: debits - credits. Only the budget's class / location."""
        if budget.class_id is not None:
            rows = [row for row in self.queries.totals(company_id, "class", start, end) if row[0] == budget.class_id]
        elif budget.location_id is not None:
            rows = [row for row in self.queries.totals(company_id, "location", start, end) if row[0] == budget.location_id]
        else:
            rows = self.queries.totals(company_id, "class", start, end)

        accounts = {}
        for account in self.account_repository.list_all(company_id):
            accounts[account.id] = account

        result = {}
        for _value, account_id, debit, credit in rows:
            account = accounts.get(account_id)
            if account is None or account.account_type not in BUDGET_TYPES:
                continue
            amount = Decimal(credit) - Decimal(debit)
            if account.account_type == AccountType.EXPENSE:
                amount = -amount
            result[account_id] = result.get(account_id, ZERO) + amount
        return result
