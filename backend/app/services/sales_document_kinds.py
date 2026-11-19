"""
How each kind of sales form behaves.

Every kind answers the same few questions (Strategy pattern):
- what status does a new one start with?
- does it post to the ledger, and is it a sale or a return?
- which account receives or pays the money?
- what is the "other side" of its journal entry?

To add a new kind of sales form, write a new class here and add it to
ALL_KINDS. SalesDocumentService does not change.
"""

from app.core.exceptions import BusinessRuleError
from app.models import Account, SalesDocument
from app.models.enums import AccountType, JournalSource, SalesDocStatus, SalesDocType
from app.repositories.account_repository import AccountRepository
from app.seed.default_accounts import SystemAccount
from app.services.ledger_service import LedgerLine
from app.services.system_accounts import SystemAccounts


class SalesDocumentKind:
    doc_type: SalesDocType
    label = ""
    initial_status = SalesDocStatus.OPEN
    # None means this form does not touch the ledger (estimates, delayed charges).
    journal_source: JournalSource | None = None
    # True for credit memos and refunds: income goes down instead of up.
    is_return = False

    def choose_money_account(
        self,
        company_id: int,
        account_id: int | None,
        accounts: AccountRepository,
        system_accounts: SystemAccounts,
    ) -> Account | None:
        return None

    def other_side(self, company_id: int, document: SalesDocument, system_accounts: SystemAccounts) -> list[LedgerLine]:
        return []


class EstimateKind(SalesDocumentKind):
    doc_type = SalesDocType.ESTIMATE
    label = "Estimate"
    initial_status = SalesDocStatus.PENDING


class DelayedChargeKind(SalesDocumentKind):
    doc_type = SalesDocType.DELAYED_CHARGE
    label = "Delayed charge"


class DelayedCreditKind(SalesDocumentKind):
    doc_type = SalesDocType.DELAYED_CREDIT
    label = "Delayed credit"


class SalesReceiptKind(SalesDocumentKind):
    """Paid on the spot: Debit bank (or Undeposited Funds), Credit income."""

    doc_type = SalesDocType.SALES_RECEIPT
    label = "Sales receipt"
    initial_status = SalesDocStatus.PAID
    journal_source = JournalSource.SALES_RECEIPT

    def choose_money_account(self, company_id, account_id, accounts, system_accounts):
        if account_id is None:
            return system_accounts.get(company_id, SystemAccount.UNDEPOSITED_FUNDS)
        account = accounts.get(company_id, account_id)
        is_allowed = (
            account is not None
            and account.is_active
            and account.account_type == AccountType.ASSET
            and account.system_key != SystemAccount.ACCOUNTS_RECEIVABLE
        )
        if not is_allowed:
            raise BusinessRuleError("Deposit the money into a bank or other asset account.")
        return account

    def other_side(self, company_id, document, system_accounts):
        return [LedgerLine(document.money_account_id, debit=document.total)]


class CreditMemoKind(SalesDocumentKind):
    """Customer credit: Debit income, Credit Accounts Receivable."""

    doc_type = SalesDocType.CREDIT_MEMO
    label = "Credit memo"
    initial_status = SalesDocStatus.OPEN
    journal_source = JournalSource.CREDIT_MEMO
    is_return = True

    def other_side(self, company_id, document, system_accounts):
        receivable = system_accounts.get(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)
        return [LedgerLine(receivable.id, credit=document.total)]


class RefundReceiptKind(SalesDocumentKind):
    """Money given back: Debit income, Credit the bank or card it was paid from."""

    doc_type = SalesDocType.REFUND_RECEIPT
    label = "Refund receipt"
    initial_status = SalesDocStatus.PAID
    journal_source = JournalSource.REFUND_RECEIPT
    is_return = True

    def choose_money_account(self, company_id, account_id, accounts, system_accounts):
        account = None
        if account_id is not None:
            account = accounts.get(company_id, account_id)
        is_allowed = (
            account is not None
            and account.is_active
            and account.account_type in (AccountType.ASSET, AccountType.LIABILITY)
            and account.system_key not in (SystemAccount.ACCOUNTS_RECEIVABLE, SystemAccount.ACCOUNTS_PAYABLE)
        )
        if not is_allowed:
            raise BusinessRuleError("Choose the bank or credit card account the refund is paid from.")
        return account

    def other_side(self, company_id, document, system_accounts):
        return [LedgerLine(document.money_account_id, credit=document.total)]


ALL_KINDS = [
    EstimateKind(),
    SalesReceiptKind(),
    CreditMemoKind(),
    RefundReceiptKind(),
    DelayedChargeKind(),
    DelayedCreditKind(),
]
