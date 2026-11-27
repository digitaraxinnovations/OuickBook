"""
Checks on upkeep: categories, bank review, reconciliation and deposits.
"""

from datetime import date, timedelta

from app.core.config import Settings
from app.core.money import ZERO, to_money
from app.health.base import HealthCheck
from app.models.enums import ReconciliationStatus
from app.repositories.banking_repositories import BankTransactionRepository, ReconciliationRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.sales_repositories import PaymentRepository, SalesDocumentRepository
from app.schemas.health import Severity
from app.seed.default_accounts import SystemAccount


class UncategorizedCheck(HealthCheck):
    name = "Uncategorized"
    severity = Severity.MEDIUM

    def __init__(self, journal: JournalRepository):
        self.journal = journal

    def run(self, company_id: int, today: date):
        for totals in self.journal.totals_by_account(company_id, None, today):
            if totals.account.system_key == SystemAccount.UNCATEGORIZED_EXPENSE and totals.balance != ZERO:
                detail = f"{totals.balance:,.2f} is in {totals.account.name}. Move it to the right category."
                return [self.finding(f"uncategorized:{totals.balance}", "Spending without a category", detail, "/accounting/chart-of-accounts")]
        return []


class BankReviewCheck(HealthCheck):
    name = "Bank lines to review"
    severity = Severity.MEDIUM

    def __init__(self, bank_transactions: BankTransactionRepository, journal: JournalRepository):
        self.bank_transactions = bank_transactions
        self.journal = journal

    def run(self, company_id: int, today: date):
        counts = self.bank_transactions.review_counts(company_id)
        if not counts:
            return []
        names = {totals.account.id: totals.account.name for totals in self.journal.totals_by_account(company_id, None, today)}
        latest = self.bank_transactions.last_imported(company_id)
        result = []
        for account_id, count in counts.items():
            name = names.get(account_id, "a bank account")
            key = f"bank-review:{account_id}:{count}:{latest.get(account_id)}"
            result.append(self.finding(key, f"Bank lines waiting in {name}", f"{count} line(s) are not in your books yet.", "/banking"))
        return result


class ReconcileCheck(HealthCheck):
    name = "Reconciliation"
    severity = Severity.MEDIUM

    def __init__(self, settings: Settings, journal: JournalRepository, reconciliations: ReconciliationRepository):
        self.settings = settings
        self.journal = journal
        self.reconciliations = reconciliations

    def run(self, company_id: int, today: date):
        days = self.settings.health_reconcile_days
        cutoff = today - timedelta(days=days)
        result = []
        # Accounts that already had activity before the cut-off.
        for totals in self.journal.bank_totals(company_id, cutoff):
            account = totals.account
            done = [
                item.statement_date
                for item in self.reconciliations.list_for_account(company_id, account.id)
                if item.status == ReconciliationStatus.COMPLETED
            ]
            last = max(done) if done else None
            if last is not None and last >= cutoff:
                continue
            detail = f"Last reconciled {last.isoformat()}." if last else "It has never been reconciled."
            result.append(
                self.finding(f"reconcile:{account.id}:{last}", f"{account.name} not reconciled for {days}+ days", detail, "/banking/reconcile")
            )
        return result


class UndepositedCheck(HealthCheck):
    name = "Undeposited money"
    severity = Severity.MEDIUM

    def __init__(
        self,
        settings: Settings,
        journal: JournalRepository,
        payments: PaymentRepository,
        sales_documents: SalesDocumentRepository,
    ):
        self.settings = settings
        self.journal = journal
        self.payments = payments
        self.sales_documents = sales_documents

    def run(self, company_id: int, today: date):
        holding = [
            totals.account
            for totals in self.journal.totals_by_account(company_id, None, today)
            if totals.account.system_key == SystemAccount.UNDEPOSITED_FUNDS
        ]
        if not holding:
            return []
        cutoff = today - timedelta(days=self.settings.health_undeposited_days)
        amounts = [
            to_money(payment.amount * payment.exchange_rate)
            for payment in self.payments.list_undeposited(company_id, holding[0].id)
            if payment.payment_date < cutoff
        ]
        amounts += [
            to_money(receipt.total * receipt.exchange_rate)
            for receipt in self.sales_documents.list_undeposited_receipts(company_id, holding[0].id)
            if receipt.doc_date < cutoff
        ]
        if not amounts:
            return []
        total = sum(amounts, ZERO)
        detail = f"{len(amounts)} receipt(s) totalling {total:,.2f} are older than {self.settings.health_undeposited_days} days."
        return [self.finding(f"undeposited:{len(amounts)}:{total}", "Money waiting to be deposited", detail, "/banking/deposits/new")]
