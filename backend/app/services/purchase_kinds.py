"""
How each kind of vendor form behaves (Strategy pattern, like sales_document_kinds.py).

- Bill:            Debit expense categories, Credit Accounts Payable.
- Vendor credit:   Debit Accounts Payable, Credit expense categories.
- Purchase order:  no ledger entry (it is only an order).
"""

from app.models import PurchaseDocument
from app.models.enums import JournalSource, PurchaseDocType
from app.seed.default_accounts import SystemAccount
from app.services.ledger_service import LedgerLine
from app.services.system_accounts import SystemAccounts


def category_ledger_lines(document: PurchaseDocument, is_return: bool) -> list[LedgerLine]:
    """
    One ledger line per form line. For a bill a positive amount is a debit
    (money spent); a vendor credit flips it.
    """
    lines = []
    for line in document.lines:
        amount = line.amount
        if is_return:
            amount = -amount
        if amount > 0:
            lines.append(LedgerLine(line.account_id, debit=amount, description=line.description))
        elif amount < 0:
            lines.append(LedgerLine(line.account_id, credit=-amount, description=line.description))
    return lines


class PurchaseKind:
    doc_type: PurchaseDocType
    label = ""
    journal_source: JournalSource | None = None
    has_due_date = False
    # Purchase orders get our own numbers; bills use the vendor's number.
    auto_number = False

    def ledger_lines(self, company_id: int, document: PurchaseDocument, system_accounts: SystemAccounts) -> list[LedgerLine]:
        return []


class BillKind(PurchaseKind):
    doc_type = PurchaseDocType.BILL
    label = "Bill"
    journal_source = JournalSource.BILL
    has_due_date = True

    def ledger_lines(self, company_id, document, system_accounts):
        payable = system_accounts.get(company_id, SystemAccount.ACCOUNTS_PAYABLE)
        lines = category_ledger_lines(document, is_return=False)
        lines.append(LedgerLine(payable.id, credit=document.total))
        return lines


class VendorCreditKind(PurchaseKind):
    doc_type = PurchaseDocType.VENDOR_CREDIT
    label = "Vendor credit"
    journal_source = JournalSource.VENDOR_CREDIT

    def ledger_lines(self, company_id, document, system_accounts):
        payable = system_accounts.get(company_id, SystemAccount.ACCOUNTS_PAYABLE)
        lines = [LedgerLine(payable.id, debit=document.total)]
        lines.extend(category_ledger_lines(document, is_return=True))
        return lines


class PurchaseOrderKind(PurchaseKind):
    doc_type = PurchaseDocType.PURCHASE_ORDER
    label = "Purchase order"
    auto_number = True


ALL_PURCHASE_KINDS = [BillKind(), VendorCreditKind(), PurchaseOrderKind()]
