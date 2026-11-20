"""
Late fees: once an invoice is past due (plus the grace days), add a
one-time late fee line to it.

    Debit  Accounts Receivable
    Credit Late Fee Income
"""

from datetime import date, timedelta

from app.core.money import to_money
from app.models import InvoiceLine
from app.models.enums import JournalSource
from app.repositories.company_repository import CompanyRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.sales_extras import BatchResult
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts


class LateFeeService(BaseService):
    def __init__(
        self,
        session,
        invoice_repository: InvoiceRepository,
        company_repository: CompanyRepository,
        system_accounts: SystemAccounts,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.invoice_repository = invoice_repository
        self.company_repository = company_repository
        self.system_accounts = system_accounts
        self.ledger = ledger

    def apply_due(self, company_id: int, today: date) -> BatchResult:
        company = self.company_repository.get(company_id)
        if not company.late_fee_enabled or company.late_fee_amount <= 0:
            return BatchResult(count=0, details=["Late fees are turned off in Sales settings."])

        income_account = self.system_accounts.get(company_id, SystemAccount.LATE_FEE_INCOME)
        receivable = self.system_accounts.get(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)
        details = []

        for invoice in self.invoice_repository.list_unpaid(company_id):
            fee_starts_on = invoice.due_date + timedelta(days=company.late_fee_grace_days + 1)
            if invoice.late_fee_applied_on is not None or today < fee_starts_on:
                continue

            if company.late_fee_type == "PERCENT":
                fee = to_money(invoice.balance_due * company.late_fee_amount / 100)
            else:
                fee = to_money(company.late_fee_amount)
            if fee <= 0:
                continue

            invoice.lines.append(
                InvoiceLine(
                    income_account_id=income_account.id,
                    description=f"Late fee (applied {today.isoformat()})",
                    quantity=1,
                    rate=fee,
                    amount=fee,
                    is_late_fee=True,
                )
            )
            invoice.total = invoice.total + fee
            invoice.late_fee_applied_on = today
            self.ledger.post(
                company_id=company_id,
                entry_date=today,
                source_type=JournalSource.LATE_FEE,
                source_id=invoice.id,
                memo=f"Late fee on invoice {invoice.invoice_number}",
                lines=[
                    LedgerLine(receivable.id, debit=to_money(fee * invoice.exchange_rate)),
                    LedgerLine(income_account.id, credit=to_money(fee * invoice.exchange_rate)),
                ],
            )
            details.append(f"Invoice {invoice.invoice_number}: late fee {fee}")

        self.commit()
        return BatchResult(count=len(details), details=details)
