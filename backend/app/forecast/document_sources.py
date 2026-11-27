"""
Money already on the books: unpaid invoices, unpaid bills, money not yet
deposited and sales tax owed.
"""

from datetime import date, timedelta

from app.core.money import ZERO, to_money
from app.forecast.base import CashSource
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.seed.default_accounts import SystemAccount
from app.services.payment_score_service import PaymentScoreService
from app.services.tax_service import TaxService


class OpenInvoiceSource(CashSource):
    label = "Invoice"

    def __init__(self, invoices: InvoiceRepository, scores: PaymentScoreService):
        self.invoices = invoices
        self.scores = scores

    def items(self, company_id, today: date, end: date):
        # Customers who usually pay late are expected that many days after the due date.
        delays = self.scores.usual_delays(company_id)
        result = []
        for invoice in self.invoices.list_unpaid(company_id):
            expected = max(invoice.due_date + timedelta(days=delays.get(invoice.customer_id, 0)), today)
            if expected > end or invoice.balance_due <= 0:
                continue
            amount = to_money(invoice.balance_due * invoice.exchange_rate)
            description = f"Invoice {invoice.invoice_number} - {invoice.customer.display_name}"
            result.append(self.item(expected, amount, description, invoice.customer, f"/sales/invoices/{invoice.id}"))
        return result


class UnpaidBillSource(CashSource):
    label = "Bill"

    def __init__(self, bills: PurchaseDocumentRepository):
        self.bills = bills

    def items(self, company_id, today: date, end: date):
        result = []
        for bill in self.bills.list_unpaid_bills(company_id):
            expected = max(bill.due_date or today, today)
            if expected > end or bill.balance <= 0:
                continue
            amount = -to_money(bill.balance * bill.exchange_rate)
            number = f" {bill.doc_number}" if bill.doc_number else ""
            description = f"Bill{number} - {bill.vendor.display_name}"
            result.append(self.item(expected, amount, description, link=f"/expenses/forms/bills/{bill.id}"))
        return result


class UndepositedFundsSource(CashSource):
    """Payments already received that have not reached the bank yet."""

    label = "Deposit"

    def __init__(self, journal: JournalRepository):
        self.journal = journal

    def items(self, company_id, today: date, end: date):
        for totals in self.journal.totals_by_account(company_id, None, today):
            if totals.account.system_key == SystemAccount.UNDEPOSITED_FUNDS and totals.balance > ZERO:
                return [self.item(today, totals.balance, "Money received, waiting to be deposited", link="/banking/deposits/new")]
        return []


class SalesTaxSource(CashSource):
    label = "Sales tax"

    def __init__(self, taxes: TaxService, due_days: int):
        self.taxes = taxes
        self.due_days = due_days

    def items(self, company_id, today: date, end: date):
        result = []
        for period in self.taxes.periods(company_id, today=today):
            if period.status not in ("DUE", "OPEN") or period.balance <= 0:
                continue
            expected = max(period.period_end + timedelta(days=self.due_days), today)
            if expected <= end:
                description = f"{period.agency_name}, period ending {period.period_end.isoformat()}"
                result.append(self.item(expected, -period.balance, description, link="/taxes"))
        return result
