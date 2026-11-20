from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import ProjectStatus
from app.schemas.common import AccountSummary, CleanStringsModel, ContactSummary, ORMModel

# ---------- on transactions ----------


class TrackingInput(BaseModel):
    """Class, location, project and tags of a transaction. All optional."""

    class_id: int | None = None
    location_id: int | None = None
    project_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)


class TrackingRead(BaseModel):
    class_id: int | None = None
    location_id: int | None = None
    project_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)


# ---------- lists ----------


class NamedListWrite(CleanStringsModel):
    """Classes and locations."""

    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    is_active: bool = True


class NamedListRead(ORMModel):
    id: int
    name: str
    parent_id: int | None
    is_active: bool


class TagWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    group_name: str | None = Field(default=None, max_length=100)


class TagRead(ORMModel):
    id: int
    name: str
    group_name: str | None


class ProjectWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=200)
    customer_id: int
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class ProjectRead(ORMModel):
    id: int
    name: str
    customer_id: int
    status: ProjectStatus
    start_date: date | None
    end_date: date | None
    description: str | None


class ProjectTransaction(BaseModel):
    entry_date: date
    memo: str | None
    account: AccountSummary
    # Income is positive, costs are negative.
    amount: Decimal


class ProjectSummary(BaseModel):
    project: ProjectRead
    customer: ContactSummary
    income: Decimal
    costs: Decimal
    labor_cost: Decimal
    labor_hours: Decimal
    profit: Decimal
    # Profit as a percentage of income (None when there is no income).
    margin_percent: Decimal | None
    transactions: list[ProjectTransaction]


# ---------- budgets ----------


class BudgetLineInput(BaseModel):
    account_id: int
    # 12 amounts, January to December.
    months: list[Decimal] = Field(min_length=12, max_length=12)


class BudgetWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    fiscal_year: int = Field(ge=2000, le=2100)
    class_id: int | None = None
    location_id: int | None = None
    lines: list[BudgetLineInput] = Field(default_factory=list)


class BudgetLineRead(BaseModel):
    account_id: int
    account_name: str
    account_type: str
    months: list[Decimal]


class BudgetRead(BaseModel):
    id: int
    name: str
    fiscal_year: int
    class_id: int | None
    location_id: int | None
    lines: list[BudgetLineRead]


class BudgetSummary(ORMModel):
    id: int
    name: str
    fiscal_year: int
    class_id: int | None
    location_id: int | None


class BudgetVsActualRow(BaseModel):
    account_id: int
    account_name: str
    account_type: str
    budget: Decimal
    actual: Decimal
    difference: Decimal
    # Actual as a percentage of budget (None when the budget is zero).
    percent_of_budget: Decimal | None


class BudgetVsActual(BaseModel):
    budget_id: int
    name: str
    start_date: date
    end_date: date
    rows: list[BudgetVsActualRow]
    budget_net_income: Decimal
    actual_net_income: Decimal
