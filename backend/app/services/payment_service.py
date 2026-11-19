"""
Receiving customer payments.

A payment moves money from "the customer owes us" to "we have the money":
    Debit  Bank / Undeposited Funds
    Credit Accounts Receivable
"""

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import to_money
from app.models import Account, Payment
from app.models.enums import AccountType, InvoiceStatus, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService


class PaymentService(BaseService):
    def __init__(
        self,
        session,
        payment_repository: PaymentRepository,
        invoice_repository: InvoiceRepository,
        account_repository: AccountRepository,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.payment_repository = payment_repository
        self.invoice_repository = invoice_repository
        self.account_repository = account_repository
        self.ledger = ledger

    def list(self, company_id: int) -> list[Payment]:
        return self.payment_repository.list_all(company_id)

    def list_for_invoice(self, company_id: int, invoice_id: int) -> list[Payment]:
        return self.payment_repository.list_for_invoice(company_id, invoice_id)

    def receive(self, company_id: int, data: PaymentCreate) -> Payment:
        invoice = self.invoice_repository.get(company_id, data.invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        if invoice.status in (InvoiceStatus.VOID, InvoiceStatus.PAID):
            raise BusinessRuleError(f"Invoice {invoice.invoice_number} is {invoice.status.value.lower()} and cannot take a payment.")

        amount = to_money(data.amount)
        if amount > invoice.balance_due:
            raise BusinessRuleError(f"The payment is more than the balance due ({invoice.balance_due}).")

        deposit_account = self.find_deposit_account(company_id, data.deposit_account_id)
        receivable = self.account_repository.get_by_system_key(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)

        payment = Payment(
            company_id=company_id,
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            payment_date=data.payment_date,
            amount=amount,
            payment_method=data.payment_method,
            reference_no=data.reference_no,
            deposit_account_id=deposit_account.id,
            memo=data.memo,
        )
        self.payment_repository.add(payment)

        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.payment_date,
            source_type=JournalSource.PAYMENT,
            source_id=payment.id,
            memo=f"Payment for invoice {invoice.invoice_number}",
            lines=[
                LedgerLine(deposit_account.id, debit=amount),
                LedgerLine(receivable.id, credit=amount),
            ],
        )
        payment.journal_entry_id = entry.id

        invoice.amount_paid = invoice.amount_paid + amount
        if invoice.balance_due == 0:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        self.commit()
        return payment

    def find_deposit_account(self, company_id: int, account_id: int | None) -> Account:
        if account_id is None:
            return self.account_repository.get_by_system_key(company_id, SystemAccount.UNDEPOSITED_FUNDS)

        account = self.account_repository.get(company_id, account_id)
        is_allowed = (
            account is not None
            and account.is_active
            and account.account_type == AccountType.ASSET
            and account.system_key != SystemAccount.ACCOUNTS_RECEIVABLE
        )
        if not is_allowed:
            raise BusinessRuleError("Please deposit the payment into a bank or other asset account.")
        return account
