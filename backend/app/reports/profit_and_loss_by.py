"""
Profit and Loss split by class, location, tag or project.

Each class (location, tag, project) is one section: its income accounts
(positive) and expense accounts (negative), so the section total is that
class's net income. Transactions without one are in "Not specified".
"""

from datetime import date
from decimal import Decimal

from app.core.money import ZERO
from app.models.enums import AccountType
from app.reports.base import Report
from app.repositories.account_repository import AccountRepository
from app.repositories.tracking_repositories import DimensionQueries
from app.schemas.report import ReportOptions, ReportResult, ReportRow

NOT_SPECIFIED = "Not specified"


class ProfitAndLossByReport(Report):
    """Subclasses set key, title, description and `dimension`."""

    dimension = ""

    def __init__(self, queries: DimensionQueries, account_repository: AccountRepository, name_repository):
        self.queries = queries
        self.account_repository = account_repository
        self.name_repository = name_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        accounts = {}
        for account in self.account_repository.list_all(company_id):
            accounts[account.id] = account
        names = {}
        for record in self.name_repository.list_all(company_id):
            names[record.id] = record.name

        # amounts[value][account_id] = signed amount (income +, expense -)
        amounts = {}
        for value, account_id, debit, credit in self.queries.totals(company_id, self.dimension, start_date, end_date):
            account = accounts.get(account_id)
            if account is None or account.account_type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue
            amount = Decimal(credit) - Decimal(debit)
            if amount == 0:
                continue
            per_account = amounts.setdefault(value, {})
            per_account[account_id] = per_account.get(account_id, ZERO) + amount

        sections = []
        net_total = ZERO
        ordered_values = sorted((value for value in amounts if value is not None), key=lambda value: names.get(value, ""))
        if None in amounts:
            ordered_values.append(None)
        for value in ordered_values:
            rows = []
            for account_id, amount in sorted(amounts[value].items(), key=lambda item: self.sort_key(accounts[item[0]])):
                account = accounts[account_id]
                rows.append(ReportRow(label=account.name, amount=amount, account_id=account_id))
            title = names.get(value, NOT_SPECIFIED) if value is not None else NOT_SPECIFIED
            section = self.make_section(f"{title} - net income", rows)
            sections.append(section)
            if self.dimension != "tag":
                net_total += section.total

        summary = []
        if self.dimension == "tag":
            # One transaction can have several tags, so tag totals are not added together.
            summary.append(ReportRow(label="Each transaction counts under every one of its tags", amount=ZERO))
        else:
            summary.append(ReportRow(label="Net income", amount=net_total))
        return self.make_result(start_date, end_date, sections, summary)

    def sort_key(self, account):
        return (account.account_type != AccountType.INCOME, account.code or "", account.name)


class ProfitAndLossByClassReport(ProfitAndLossByReport):
    key = "profit-and-loss-by-class"
    group = "Business overview"
    title = "Profit and Loss by Class"
    description = "Income, expenses and net income for each class."
    dimension = "class"


class ProfitAndLossByLocationReport(ProfitAndLossByReport):
    key = "profit-and-loss-by-location"
    group = "Business overview"
    title = "Profit and Loss by Location"
    description = "Income, expenses and net income for each location."
    dimension = "location"


class ProfitAndLossByTagReport(ProfitAndLossByReport):
    key = "profit-and-loss-by-tag"
    group = "Business overview"
    title = "Profit and Loss by Tag"
    description = "Income, expenses and net income of the transactions with each tag."
    dimension = "tag"


class ProjectProfitabilityReport(ProfitAndLossByReport):
    key = "project-profitability"
    group = "Business overview"
    title = "Project Profitability"
    description = "Income, costs and profit of each project (labor cost is on each project's page)."
    dimension = "project"
