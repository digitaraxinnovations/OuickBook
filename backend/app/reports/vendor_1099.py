"""
1099 summary: how much each contractor (vendor marked "track 1099") was paid,
per 1099 box, for the period.

Rules (same as the original product):
- Only money actually paid counts: expenses, checks and bill payments.
- Payments by credit card are left out - the card company reports those.
- The box comes from the expense account (Chart of accounts -> 1099 box).
- Only vendors paid at least the threshold (default 600) are shown.
"""

from datetime import date
from decimal import Decimal

from app.core.money import ZERO, to_money
from app.models.enums import AccountType, PaymentMethod
from app.reports.base import Report
from app.repositories.contact_repository import VendorRepository
from app.repositories.purchase_repositories import BillPaymentRepository, ExpenseQueries
from app.schemas.report import ReportResult, ReportRow
from app.seed.default_accounts import FORM_1099_BOXES


def paid_by_card(payment_method: PaymentMethod, account) -> bool:
    return payment_method == PaymentMethod.CREDIT_CARD or account.account_type == AccountType.LIABILITY


class Vendor1099Report(Report):
    key = "1099-summary"
    title = "1099 Contractor Summary"
    description = "Payments to 1099 contractors per 1099 box, excluding card payments."

    def __init__(
        self,
        vendor_repository: VendorRepository,
        expense_queries: ExpenseQueries,
        bill_payment_repository: BillPaymentRepository,
        threshold: int,
    ):
        self.vendor_repository = vendor_repository
        self.expense_queries = expense_queries
        self.bill_payment_repository = bill_payment_repository
        self.threshold = Decimal(threshold)

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        vendors = {}
        for vendor in self.vendor_repository.list_all(company_id):
            if vendor.track_1099:
                vendors[vendor.id] = vendor

        # totals[(vendor_id, box)] = amount
        totals = {}

        for expense in self.expense_queries.list_between(company_id, start_date, end_date):
            if expense.vendor_id is None or paid_by_card(expense.payment_method, expense.payment_account):
                continue
            for line in expense.lines:
                self.add_amount(totals, vendors, expense.vendor_id, line.account.box_1099, line.amount)

        for payment in self.bill_payment_repository.list_between(company_id, start_date, end_date):
            if paid_by_card(payment.payment_method, payment.payment_account) or payment.amount <= 0:
                continue
            applied_total = ZERO
            for application in payment.applications:
                applied_total += application.amount
            # Only the cash part of the payment counts (vendor credits used are not payments).
            cash_share = payment.amount / applied_total
            for application in payment.applications:
                bill = application.bill
                for line in bill.lines:
                    share_of_bill = line.amount / bill.total
                    amount = to_money(application.amount * cash_share * share_of_bill)
                    self.add_amount(totals, vendors, payment.vendor_id, line.account.box_1099, amount)

        # Vendor totals decide who is over the threshold.
        vendor_totals = {}
        for (vendor_id, _box), amount in totals.items():
            vendor_totals[vendor_id] = vendor_totals.get(vendor_id, ZERO) + amount

        sections = []
        grand_total = ZERO
        below_threshold = 0
        for vendor_id, amount in vendor_totals.items():
            if amount < self.threshold:
                below_threshold += 1

        for box, box_label in FORM_1099_BOXES.items():
            rows = []
            for (vendor_id, row_box), amount in totals.items():
                if row_box != box or vendor_totals[vendor_id] < self.threshold:
                    continue
                vendor = vendors[vendor_id]
                label = vendor.display_name
                if vendor.tax_id:
                    label = label + " (Tax ID " + vendor.tax_id + ")"
                rows.append(ReportRow(label=label, amount=amount))
            if rows:
                section = self.make_section(box_label, rows)
                sections.append(section)
                grand_total += section.total

        summary = [ReportRow(label="Total reportable payments", amount=grand_total)]
        if below_threshold:
            summary.append(ReportRow(label=f"Contractors below the {self.threshold:.0f} threshold (not shown)", amount=Decimal(below_threshold)))
        return self.make_result(start_date, end_date, sections, summary)

    def add_amount(self, totals: dict, vendors: dict, vendor_id: int, box: str | None, amount: Decimal) -> None:
        """Add a payment to totals[(vendor, box)] - only for 1099 vendors and accounts with a box."""
        if box is None or vendor_id not in vendors:
            return
        key = (vendor_id, box)
        totals[key] = totals.get(key, ZERO) + amount
