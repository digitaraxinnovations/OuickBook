"""
Checks on money going out: duplicates, unusual amounts and missing receipts.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from app.core.config import Settings
from app.core.money import to_money
from app.health.base import HealthCheck
from app.models.enums import ExpenseKind, PurchaseDocStatus, PurchaseDocType
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.purchase_repositories import AttachmentRepository, PurchaseDocumentRepository
from app.schemas.health import Severity


@dataclass
class Spend:
    """One bill or expense, in the shape the checks need."""

    kind: str  # "bill" or "expense"
    id: int
    vendor_id: int | None
    vendor_name: str
    date: date
    amount: Decimal  # home currency

    @property
    def link(self) -> str:
        return f"/expenses/forms/bills/{self.id}" if self.kind == "bill" else f"/expenses/{self.id}"

    @property
    def label(self) -> str:
        """"a bill of 60.00 on ..." / "an expense of ..." - ready to use in a sentence."""
        article = "an" if self.kind == "expense" else "a"
        return f"{article} {self.kind} of {self.amount:,.2f} on {self.date.isoformat()}"


class SpendingList:
    """Bills and expenses that are not void, oldest first."""

    def __init__(self, bills: PurchaseDocumentRepository, expenses: ExpenseRepository):
        self.bills = bills
        self.expenses = expenses

    def all(self, company_id: int) -> list[Spend]:
        result = []
        for bill in self.bills.list_filtered(company_id, doc_type=PurchaseDocType.BILL):
            if bill.status != PurchaseDocStatus.VOID:
                amount = to_money(bill.total * bill.exchange_rate)
                result.append(Spend("bill", bill.id, bill.vendor_id, bill.vendor.display_name, bill.doc_date, amount))
        for expense in self.expenses.list_all(company_id):
            if not expense.is_void and expense.kind != ExpenseKind.CARD_CREDIT:
                name = expense.vendor.display_name if expense.vendor else "no vendor"
                amount = to_money(expense.total * expense.exchange_rate)
                result.append(Spend("expense", expense.id, expense.vendor_id, name, expense.expense_date, amount))
        result.sort(key=lambda spend: (spend.date, spend.kind, spend.id))
        return result


class DuplicateSpendingCheck(HealthCheck):
    name = "Possible duplicates"
    severity = Severity.HIGH

    def __init__(self, settings: Settings, spending: SpendingList):
        self.settings = settings
        self.spending = spending

    def run(self, company_id: int, today: date):
        since = today - timedelta(days=self.settings.health_lookback_days)
        groups: dict[tuple, list[Spend]] = {}
        for spend in self.spending.all(company_id):
            if spend.vendor_id is not None and spend.date >= since:
                groups.setdefault((spend.vendor_id, spend.amount), []).append(spend)

        result = []
        for group in groups.values():
            for first, second in zip(group, group[1:]):
                if (second.date - first.date).days <= self.settings.health_duplicate_days:
                    key = f"duplicate:{first.kind}{first.id}:{second.kind}{second.id}"
                    title = f"{second.vendor_name} may be entered twice"
                    detail = f"There is {first.label} and {second.label}."
                    result.append(self.finding(key, title, detail, second.link))
        return result


class UnusualAmountCheck(HealthCheck):
    name = "Unusual amounts"
    severity = Severity.MEDIUM

    def __init__(self, settings: Settings, spending: SpendingList):
        self.settings = settings
        self.spending = spending

    def run(self, company_id: int, today: date):
        since = today - timedelta(days=self.settings.health_lookback_days)
        earlier: dict[int, list[Decimal]] = {}
        result = []
        for spend in self.spending.all(company_id):
            if spend.vendor_id is None:
                continue
            history = earlier.setdefault(spend.vendor_id, [])
            if spend.date >= since and len(history) >= self.settings.health_unusual_min_history:
                typical = to_money(median(history))
                if spend.amount > typical * self.settings.health_unusual_factor:
                    title = f"Unusually large {spend.kind} from {spend.vendor_name}"
                    detail = f"This is {spend.label}; the typical amount is {typical:,.2f}."
                    result.append(self.finding(f"unusual:{spend.kind}{spend.id}", title, detail, spend.link))
            history.append(spend.amount)
        return result


class MissingReceiptCheck(HealthCheck):
    name = "Missing receipts"
    severity = Severity.LOW

    def __init__(self, settings: Settings, spending: SpendingList, attachments: AttachmentRepository):
        self.settings = settings
        self.spending = spending
        self.attachments = attachments

    def run(self, company_id: int, today: date):
        since = today - timedelta(days=self.settings.health_lookback_days)
        result = []
        for spend in self.spending.all(company_id):
            if spend.kind != "expense" or spend.date < since or spend.amount <= self.settings.health_receipt_min:
                continue
            if not self.attachments.list_for(company_id, "EXPENSE", spend.id):
                title = f"No receipt: {spend.vendor_name}"
                result.append(self.finding(f"receipt:{spend.id}", title, f"Nothing is attached to {spend.label}.", spend.link))
        return result
