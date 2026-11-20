from datetime import date

from app.core.money import ZERO
from app.models.enums import AccountType
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.schemas.dashboard import AccountBalance, DashboardSummary
from app.seed.default_accounts import DetailType


class DashboardService:
    """Numbers for the home screen."""

    def __init__(
        self,
        journal_repository: JournalRepository,
        invoice_repository: InvoiceRepository,
        purchase_repository: PurchaseDocumentRepository,
    ):
        self.journal_repository = journal_repository
        self.invoice_repository = invoice_repository
        self.purchase_repository = purchase_repository

    def get_summary(self, company_id: int, start_date: date | None = None, end_date: date | None = None) -> DashboardSummary:
        today = date.today()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = date(end_date.year, 1, 1)

        income = ZERO
        expenses = ZERO
        for totals in self.journal_repository.totals_by_account(company_id, start_date, end_date):
            if totals.account.account_type == AccountType.INCOME:
                income += totals.balance
            elif totals.account.account_type == AccountType.EXPENSE:
                expenses += totals.balance

        bank_accounts = []
        for totals in self.journal_repository.totals_by_account(company_id, None, today):
            if totals.account.detail_type == DetailType.BANK:
                bank_accounts.append(
                    AccountBalance(account_id=totals.account.id, name=totals.account.name, balance=totals.balance)
                )

        open_total = ZERO
        overdue_total = ZERO
        open_count = 0
        overdue_count = 0
        for invoice in self.invoice_repository.list_unpaid(company_id):
            open_total += invoice.balance_due
            open_count += 1
            if invoice.is_overdue:
                overdue_total += invoice.balance_due
                overdue_count += 1

        bills_total = ZERO
        bills_overdue_total = ZERO
        bills_overdue_count = 0
        for bill in self.purchase_repository.list_unpaid_bills(company_id):
            bills_total += bill.balance
            if bill.is_overdue:
                bills_overdue_total += bill.balance
                bills_overdue_count += 1

        return DashboardSummary(
            period_start=start_date,
            period_end=end_date,
            income=income,
            expenses=expenses,
            net_income=income - expenses,
            open_invoices_total=open_total,
            open_invoice_count=open_count,
            overdue_invoices_total=overdue_total,
            overdue_invoice_count=overdue_count,
            bank_accounts=bank_accounts,
            unpaid_bills_total=bills_total,
            overdue_bills_total=bills_overdue_total,
            overdue_bill_count=bills_overdue_count,
        )
