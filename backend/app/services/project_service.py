"""
Project profitability.

    Income       income accounts posted with the project
    Costs        expense accounts posted with the project (bills, expenses, cost of goods sold...)
    Labor cost   hours on the project's time entries x each hourly employee's pay rate
    Profit       income - costs - labor cost
"""

from decimal import Decimal

from app.core.money import ZERO, to_money
from app.models.enums import AccountType, PayType
from app.repositories.contact_repository import CustomerRepository
from app.repositories.tracking_repositories import ProjectRepository
from app.schemas.common import ContactSummary
from app.schemas.tracking import ProjectRead, ProjectSummary, ProjectTransaction
from app.services.tracking_service import TrackingService


class ProjectService:
    def __init__(self, project_repository: ProjectRepository, customer_repository: CustomerRepository, tracking: TrackingService):
        self.project_repository = project_repository
        self.customer_repository = customer_repository
        self.tracking = tracking

    def summary(self, company_id: int, project_id: int) -> ProjectSummary:
        project = self.tracking.get_project(company_id, project_id)
        customer = self.customer_repository.get(company_id, project.customer_id)

        income = ZERO
        costs = ZERO
        transactions = []
        for line in self.project_repository.lines_for(company_id, project.id):
            account_type = line.account.account_type
            if account_type == AccountType.INCOME:
                amount = line.credit - line.debit
                income += amount
            elif account_type == AccountType.EXPENSE:
                amount = -(line.debit - line.credit)
                costs += -amount
            else:
                continue
            transactions.append(
                ProjectTransaction(
                    entry_date=line.entry.entry_date,
                    memo=line.entry.memo,
                    account=line.account,
                    amount=amount,
                )
            )

        labor_cost = ZERO
        labor_hours = ZERO
        for entry in self.project_repository.time_for(company_id, project.id):
            labor_hours += entry.hours
            employee = entry.employee
            if employee is not None and employee.pay_type == PayType.HOURLY:
                labor_cost += entry.hours * employee.pay_rate
        labor_cost = to_money(labor_cost)

        profit = income - costs - labor_cost
        margin = None
        if income != 0:
            margin = to_money(profit * Decimal("100") / income)

        transactions.sort(key=lambda item: item.entry_date, reverse=True)
        return ProjectSummary(
            project=ProjectRead.model_validate(project),
            customer=ContactSummary.model_validate(customer),
            income=income,
            costs=costs,
            labor_cost=labor_cost,
            labor_hours=labor_hours,
            profit=profit,
            margin_percent=margin,
            transactions=transactions,
        )
