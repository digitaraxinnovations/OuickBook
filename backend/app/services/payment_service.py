"""
Receiving customer payments.

One payment can pay several invoices, can use the customer's existing
credits (credit memos, earlier overpayments) and can be more than the
invoices - the extra stays with the customer as a credit.

Ledger (only the money actually received is posted):
    Debit  Bank / Undeposited Funds
    Credit Accounts Receivable
Using a credit posts nothing: the credit memo or overpayment already
lowered Accounts Receivable when it was recorded.
"""

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import Account, CreditApplication, Payment, PaymentApplication
from app.models.enums import (
    AccountType,
    CreditSource,
    InvoiceStatus,
    JournalSource,
    SalesDocStatus,
    SalesDocType,
)
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.sales_repositories import PaymentRepository, SalesDocumentRepository
from app.schemas.payment import CustomerCredit, PaymentCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts


class PaymentService(BaseService):
    def __init__(
        self,
        session,
        payment_repository: PaymentRepository,
        invoice_repository: InvoiceRepository,
        customer_repository: CustomerRepository,
        sales_document_repository: SalesDocumentRepository,
        account_repository: AccountRepository,
        system_accounts: SystemAccounts,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.payment_repository = payment_repository
        self.invoice_repository = invoice_repository
        self.customer_repository = customer_repository
        self.sales_document_repository = sales_document_repository
        self.account_repository = account_repository
        self.system_accounts = system_accounts
        self.ledger = ledger

    # ---------- reading ----------

    def list(self, company_id: int) -> list[Payment]:
        return self.payment_repository.list_all(company_id)

    def get(self, company_id: int, payment_id: int) -> Payment:
        payment = self.payment_repository.get(company_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment not found.")
        return payment

    def list_for_invoice(self, company_id: int, invoice_id: int) -> list[dict]:
        rows = []
        for application in self.payment_repository.applications_for_invoice(company_id, invoice_id):
            payment = application.payment
            rows.append(
                {
                    "payment_id": payment.id,
                    "payment_date": payment.payment_date,
                    "payment_method": payment.payment_method.value,
                    "reference_no": payment.reference_no,
                    "deposit_account": payment.deposit_account,
                    "amount": application.amount,
                }
            )
        return rows

    def list_customer_credits(self, company_id: int, customer_id: int) -> list[CustomerCredit]:
        credits = []
        memos = self.sales_document_repository.list_filtered(
            company_id, SalesDocType.CREDIT_MEMO, customer_id, SalesDocStatus.OPEN
        )
        for memo in memos:
            if memo.remaining > 0:
                credits.append(
                    CustomerCredit(
                        source_type=CreditSource.CREDIT_MEMO,
                        source_id=memo.id,
                        reference="Credit memo " + memo.doc_number,
                        credit_date=memo.doc_date,
                        remaining=memo.remaining,
                    )
                )
        for payment in self.payment_repository.list_for_customer(company_id, customer_id):
            if payment.unapplied_amount > 0:
                credits.append(
                    CustomerCredit(
                        source_type=CreditSource.PAYMENT,
                        source_id=payment.id,
                        reference="Unapplied payment #" + str(payment.id),
                        credit_date=payment.payment_date,
                        remaining=payment.unapplied_amount,
                    )
                )
        return credits

    # ---------- receiving ----------

    def receive(self, company_id: int, data: PaymentCreate, commit: bool = True) -> Payment:
        customer = self.customer_repository.get(company_id, data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found.")

        amount = to_money(data.amount)
        applied_total = ZERO
        for application in data.applications:
            applied_total += application.amount
        credits_total = ZERO
        for credit in data.credits:
            credits_total += credit.amount

        if amount == 0 and credits_total == 0:
            raise BusinessRuleError("Enter the amount received or choose a credit to use.")
        if credits_total > applied_total:
            raise BusinessRuleError("Credits can only be used to pay invoices. Apply them to an invoice.")
        money_used_on_invoices = applied_total - credits_total
        if money_used_on_invoices > amount:
            raise BusinessRuleError(
                f"The invoices you chose ({applied_total}) are more than the amount received plus credits ({amount + credits_total})."
            )

        deposit_account = self.find_deposit_account(company_id, data.deposit_account_id)
        payment = Payment(
            company_id=company_id,
            customer_id=customer.id,
            payment_date=data.payment_date,
            amount=amount,
            unapplied_amount=amount - money_used_on_invoices,
            payment_method=data.payment_method,
            reference_no=data.reference_no,
            deposit_account_id=deposit_account.id,
            memo=data.memo,
        )

        # Pay the invoices.
        seen_invoices = set()
        for application in data.applications:
            if application.invoice_id in seen_invoices:
                raise BusinessRuleError("Each invoice can only appear once in a payment.")
            seen_invoices.add(application.invoice_id)

            invoice = self.invoice_repository.get(company_id, application.invoice_id)
            if invoice is None or invoice.customer_id != customer.id:
                raise BusinessRuleError(f"Invoice {application.invoice_id} does not belong to this customer.")
            if invoice.status not in (InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID):
                raise BusinessRuleError(f"Invoice {invoice.invoice_number} is not open.")
            if application.amount > invoice.balance_due:
                raise BusinessRuleError(
                    f"The amount for invoice {invoice.invoice_number} is more than its balance ({invoice.balance_due})."
                )
            payment.applications.append(PaymentApplication(invoice_id=invoice.id, amount=application.amount))
            invoice.amount_paid = invoice.amount_paid + application.amount
            if invoice.balance_due == 0:
                invoice.status = InvoiceStatus.PAID
            else:
                invoice.status = InvoiceStatus.PARTIALLY_PAID

        # Use the credits.
        for credit in data.credits:
            self.use_credit(company_id, customer.id, credit.source_type, credit.source_id, credit.amount)
            payment.credits_used.append(
                CreditApplication(source_type=credit.source_type, source_id=credit.source_id, amount=credit.amount)
            )

        self.payment_repository.add(payment)

        if amount > 0:
            receivable = self.system_accounts.get(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)
            entry = self.ledger.post(
                company_id=company_id,
                entry_date=data.payment_date,
                source_type=JournalSource.PAYMENT,
                source_id=payment.id,
                memo=f"Payment from {customer.display_name}",
                lines=[
                    LedgerLine(deposit_account.id, debit=amount),
                    LedgerLine(receivable.id, credit=amount),
                ],
            )
            payment.journal_entry_id = entry.id

        if commit:
            self.commit()
        return payment

    def use_credit(self, company_id: int, customer_id: int, source_type: CreditSource, source_id: int, amount) -> None:
        if source_type == CreditSource.CREDIT_MEMO:
            memo = self.sales_document_repository.get(company_id, source_id)
            if memo is None or memo.doc_type != SalesDocType.CREDIT_MEMO or memo.customer_id != customer_id:
                raise BusinessRuleError("That credit memo does not belong to this customer.")
            if memo.status != SalesDocStatus.OPEN or amount > memo.remaining:
                raise BusinessRuleError(f"Credit memo {memo.doc_number} only has {memo.remaining} left.")
            memo.amount_applied = memo.amount_applied + amount
            if memo.remaining == 0:
                memo.status = SalesDocStatus.CLOSED
        else:
            earlier = self.payment_repository.get(company_id, source_id)
            if earlier is None or earlier.customer_id != customer_id:
                raise BusinessRuleError("That earlier payment does not belong to this customer.")
            if amount > earlier.unapplied_amount:
                raise BusinessRuleError(f"Payment #{earlier.id} only has {earlier.unapplied_amount} of unused credit.")
            earlier.unapplied_amount = earlier.unapplied_amount - amount

    def find_deposit_account(self, company_id: int, account_id: int | None) -> Account:
        if account_id is None:
            return self.system_accounts.get(company_id, SystemAccount.UNDEPOSITED_FUNDS)

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
