"""
Profit and Loss (income statement).

Sections, like the original product:
    Income, Cost of Goods Sold  -> Gross profit
    Expenses                    -> Net operating income
    Other income                -> Net income

Options:
- basis:      accrual or cash
- column_by:  total, month, quarter, year, customer, vendor, class or location
- compare:    previous period or previous year (with $ and % change)
- filters:    class, location, customer, project
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.dates import add_months
from app.core.money import ZERO, to_money
from app.models.enums import AccountType
from app.reports.base import Report
from app.reports.report_data import Fact, LedgerFacts, ListNames, filter_facts
from app.schemas.report import ReportOptions, ReportResult, ReportRow, ReportSection

NOT_SPECIFIED = "Not specified"
SECTION_TITLES = ["Income", "Cost of Goods Sold", "Expenses", "Other Income"]


def section_of(account) -> str:
    if account.account_type == AccountType.INCOME:
        if account.detail_type == "Other Income":
            return "Other Income"
        return "Income"
    if account.detail_type == "Cost of Goods Sold" or "COGS" in (account.detail_type or ""):
        return "Cost of Goods Sold"
    return "Expenses"


def shown_amount(fact: Fact) -> Decimal:
    """Income shown positive; expenses shown positive too (they are subtracted in the totals)."""
    if fact.account.account_type == AccountType.EXPENSE:
        return -fact.amount
    return fact.amount


# ---------- columns ----------


def month_start(day: date) -> date:
    return day.replace(day=1)


def period_columns(start: date, end: date, column_by: str) -> list[tuple[str, date, date]]:
    """(label, first day, last day) for each month / quarter / year between start and end."""
    columns = []
    if column_by == "month":
        step = 1
        current = month_start(start)
    elif column_by == "quarter":
        step = 3
        current = date(start.year, ((start.month - 1) // 3) * 3 + 1, 1)
    else:
        step = 12
        current = date(start.year, 1, 1)
    while current <= end:
        last = add_months(current, step) - timedelta(days=1)
        if column_by == "month":
            label = current.strftime("%b %Y")
        elif column_by == "quarter":
            label = f"Q{(current.month - 1) // 3 + 1} {current.year}"
        else:
            label = str(current.year)
        columns.append((label, max(current, start), min(last, end)))
        current = add_months(current, step)
    return columns


class ProfitAndLossReport(Report):
    key = "profit-and-loss"
    title = "Profit and Loss"
    description = "Income minus expenses for a period. Shows whether you made money."
    group = "Business overview"
    options = ["basis", "column_by", "compare", "class_id", "location_id", "customer_id", "project_id"]

    def __init__(self, facts: LedgerFacts, list_names: ListNames):
        self.facts = facts
        self.list_names = list_names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        start = start_date or date(end_date.year, 1, 1)
        facts = filter_facts(self.facts.profit_and_loss(company_id, start, end_date, options.basis), options)
        notes = []

        if options.column_by in ("month", "quarter", "year"):
            columns = period_columns(start, end_date, options.column_by)
            labels = [label for label, _first, _last in columns] + ["Total"]

            def column_of(fact: Fact) -> int:
                for index, (_label, first, last) in enumerate(columns):
                    if first <= fact.when <= last:
                        return index
                return 0

            return self.build(start_date, end_date, options, facts, labels, column_of, notes)

        if options.column_by in ("customer", "vendor", "class", "location"):
            names = self.list_names.for_kind(company_id, options.column_by)
            keys = sorted({self.dimension_value(fact, options.column_by) for fact in facts}, key=lambda value: (value is None, names.get(value, "")))
            labels = [names.get(value, NOT_SPECIFIED) if value is not None else NOT_SPECIFIED for value in keys] + ["Total"]
            positions = {value: index for index, value in enumerate(keys)}

            def column_of(fact: Fact) -> int:
                return positions[self.dimension_value(fact, options.column_by)]

            return self.build(start_date, end_date, options, facts, labels, column_of, notes)

        if options.compare:
            prior_start, prior_end = self.prior_period(start, end_date, options.compare)
            prior = filter_facts(self.facts.profit_and_loss(company_id, prior_start, prior_end, options.basis), options)
            labels = [
                f"{start:%b %d, %Y} - {end_date:%b %d, %Y}",
                f"{prior_start:%b %d, %Y} - {prior_end:%b %d, %Y}",
                "$ change",
                "% change",
            ]
            return self.build_comparison(start_date, end_date, options, facts, prior, labels)

        return self.build(start_date, end_date, options, facts, [], None, notes)

    # ---------- building ----------

    def dimension_value(self, fact: Fact, column_by: str):
        return {
            "customer": fact.customer_id,
            "vendor": fact.vendor_id,
            "class": fact.class_id,
            "location": fact.location_id,
        }[column_by]

    def prior_period(self, start: date, end: date, compare: str) -> tuple[date, date]:
        if compare == "previous_year":
            return add_months(start, -12), add_months(end, -12)
        length = (end - start).days + 1
        prior_end = start - timedelta(days=1)
        return prior_end - timedelta(days=length - 1), prior_end

    def build(self, start_date, end_date, options, facts, labels, column_of, notes) -> ReportResult:
        """
        One row per account. With columns (`labels` not empty) each row has a
        value per column, the last column being the total.
        """
        column_count = len(labels)
        # per_account[account_id] = [amount per column] (or a single total)
        per_account = {}
        accounts = {}
        for fact in facts:
            accounts[fact.account.id] = fact.account
            amounts = per_account.setdefault(fact.account.id, [ZERO] * max(column_count, 1))
            amount = shown_amount(fact)
            if column_count:
                amounts[column_of(fact)] += amount
                amounts[-1] += amount
            else:
                amounts[0] += amount

        sections = {}
        for title in SECTION_TITLES:
            sections[title] = []
        for account_id, amounts in per_account.items():
            account = accounts[account_id]
            if all(value == 0 for value in amounts):
                continue
            row = ReportRow(label=account.name, amount=amounts[-1], account_id=account_id)
            if column_count:
                row.values = list(amounts)
            sections[section_of(account)].append(row)
        for rows in sections.values():
            rows.sort(key=lambda row: accounts[row.account_id].code or accounts[row.account_id].name)

        built = {title: self.make_section(title, rows) for title, rows in sections.items()}
        summary = self.summary_rows(built, column_count)
        shown = [section for section in built.values() if section.rows]
        return self.make_result(start_date, end_date, shown, summary, columns=labels, options=options, notes=notes)

    def summary_rows(self, built: dict[str, ReportSection], column_count: int) -> list[ReportRow]:
        def combine(plus: list[str], minus: list[str]) -> tuple[Decimal, list]:
            total = ZERO
            values = [ZERO] * column_count
            for title in plus:
                total += built[title].total
                for index, value in enumerate(built[title].totals):
                    values[index] += value or ZERO
            for title in minus:
                total -= built[title].total
                for index, value in enumerate(built[title].totals):
                    values[index] -= value or ZERO
            return total, values

        rows = []
        for label, plus, minus in (
            ("Gross profit", ["Income"], ["Cost of Goods Sold"]),
            ("Net operating income", ["Income"], ["Cost of Goods Sold", "Expenses"]),
            ("Net income", ["Income", "Other Income"], ["Cost of Goods Sold", "Expenses"]),
        ):
            total, values = combine(plus, minus)
            rows.append(ReportRow(label=label, amount=total, values=values if column_count else []))
        return rows

    def build_comparison(self, start_date, end_date, options, current_facts, prior_facts, labels) -> ReportResult:
        """Current period, prior period, $ change and % change."""
        current_result = self.build(start_date, end_date, options, current_facts, [], None, [])
        prior_result = self.build(start_date, end_date, options, prior_facts, [], None, [])

        def by_account(result: ReportResult) -> dict:
            amounts = {}
            for section in result.sections:
                for row in section.rows:
                    amounts[(section.title, row.account_id, row.label)] = row.amount
            return amounts

        current = by_account(current_result)
        prior = by_account(prior_result)
        sections = []
        for title in SECTION_TITLES:
            rows = []
            keys = sorted({key for key in list(current) + list(prior) if key[0] == title}, key=lambda key: key[2])
            for key in keys:
                now = current.get(key, ZERO)
                before = prior.get(key, ZERO)
                rows.append(ReportRow(label=key[2], amount=now, account_id=key[1], values=self.compare_values(now, before)))
            if rows:
                section = self.make_section(title, rows)
                section.totals = self.compare_values(section.total, sum((prior[key] for key in prior if key[0] == title), ZERO))
                sections.append(section)

        summary = []
        prior_summary = {row.label: row.amount for row in prior_result.summary}
        for row in current_result.summary:
            summary.append(ReportRow(label=row.label, amount=row.amount, values=self.compare_values(row.amount, prior_summary[row.label])))
        return self.make_result(start_date, end_date, sections, summary, columns=labels, options=options)

    def compare_values(self, now: Decimal, before: Decimal) -> list[Decimal | None]:
        change = now - before
        percent = to_money(change * Decimal("100") / abs(before)) if before != 0 else None
        return [now, before, change, percent]


# ---------- the same report, listed with different starting options ----------


class ProfitAndLossByMonthReport(ProfitAndLossReport):
    key = "profit-and-loss-by-month"
    title = "Profit and Loss by Month"
    description = "Income and expenses for each month of the period."
    defaults = {"column_by": "month"}


class ProfitAndLossByCustomerReport(ProfitAndLossReport):
    key = "profit-and-loss-by-customer"
    title = "Profit and Loss by Customer"
    description = "Income and expenses for each customer."
    defaults = {"column_by": "customer"}


class ProfitAndLossComparisonReport(ProfitAndLossReport):
    key = "profit-and-loss-comparison"
    title = "Profit and Loss Comparison"
    description = "This period next to the same period last year, with the change."
    defaults = {"compare": "previous_year"}
