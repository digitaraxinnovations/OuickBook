"""
Fixed lists of choices used by the models.
"""

from enum import Enum


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

    def increases_with_debit(self) -> bool:
        """Assets and expenses grow with debits; the others grow with credits."""
        return self in (AccountType.ASSET, AccountType.EXPENSE)


class ProductType(str, Enum):
    SERVICE = "SERVICE"
    NON_INVENTORY = "NON_INVENTORY"


class InvoiceStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    VOID = "VOID"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    CHECK = "CHECK"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


class RecurringFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class RecurringType(str, Enum):
    """Which kind of transaction a recurring schedule creates."""

    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    INVOICE = "INVOICE"
    SALES_RECEIPT = "SALES_RECEIPT"
    BILL = "BILL"
    EXPENSE = "EXPENSE"


class ExpenseKind(str, Enum):
    """
    EXPENSE / CHECK: money paid out (a check is an expense with a check number).
    CARD_CREDIT: a refund put back on a credit card (the reverse of an expense).
    """

    EXPENSE = "EXPENSE"
    CHECK = "CHECK"
    CARD_CREDIT = "CARD_CREDIT"


class BankTransactionStatus(str, Enum):
    FOR_REVIEW = "FOR_REVIEW"
    ADDED = "ADDED"        # a new transaction was created from it
    MATCHED = "MATCHED"    # linked to a transaction already in the books
    EXCLUDED = "EXCLUDED"  # duplicate or personal - ignored


class BankRuleDirection(str, Enum):
    MONEY_IN = "MONEY_IN"
    MONEY_OUT = "MONEY_OUT"
    ANY = "ANY"


class ReconciliationStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    UNDONE = "UNDONE"


class PurchaseDocType(str, Enum):
    """Vendor forms that share one table."""

    BILL = "BILL"
    VENDOR_CREDIT = "VENDOR_CREDIT"
    PURCHASE_ORDER = "PURCHASE_ORDER"


class PurchaseDocStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CLOSED = "CLOSED"
    VOID = "VOID"


class TripPurpose(str, Enum):
    BUSINESS = "BUSINESS"
    PERSONAL = "PERSONAL"


class SalesDocType(str, Enum):
    """Sales forms other than invoices. They share one table."""

    ESTIMATE = "ESTIMATE"
    SALES_RECEIPT = "SALES_RECEIPT"
    CREDIT_MEMO = "CREDIT_MEMO"
    REFUND_RECEIPT = "REFUND_RECEIPT"
    DELAYED_CHARGE = "DELAYED_CHARGE"
    DELAYED_CREDIT = "DELAYED_CREDIT"


class SalesDocStatus(str, Enum):
    PENDING = "PENDING"      # estimate waiting for the customer
    ACCEPTED = "ACCEPTED"    # estimate accepted (may be partly invoiced)
    REJECTED = "REJECTED"    # estimate rejected
    OPEN = "OPEN"            # credit memo with credit left, delayed charge not yet invoiced
    CLOSED = "CLOSED"        # fully used / converted / invoiced
    PAID = "PAID"            # sales receipt, refund receipt
    VOID = "VOID"


class DiscountType(str, Enum):
    PERCENT = "PERCENT"
    AMOUNT = "AMOUNT"


class CreditSource(str, Enum):
    """Where a customer credit used in a payment comes from."""

    CREDIT_MEMO = "CREDIT_MEMO"
    PAYMENT = "PAYMENT"  # the unapplied part of an earlier payment


class DepositLineSource(str, Enum):
    PAYMENT = "PAYMENT"
    SALES_RECEIPT = "SALES_RECEIPT"
    OTHER = "OTHER"


class StatementType(str, Enum):
    BALANCE_FORWARD = "BALANCE_FORWARD"
    OPEN_ITEM = "OPEN_ITEM"
    TRANSACTION = "TRANSACTION"


class JournalSource(str, Enum):
    """Which screen created a journal entry."""

    MANUAL = "MANUAL"
    INVOICE = "INVOICE"
    INVOICE_VOID = "INVOICE_VOID"
    PAYMENT = "PAYMENT"
    EXPENSE = "EXPENSE"
    SALES_RECEIPT = "SALES_RECEIPT"
    CREDIT_MEMO = "CREDIT_MEMO"
    REFUND_RECEIPT = "REFUND_RECEIPT"
    SALES_DOC_VOID = "SALES_DOC_VOID"
    DEPOSIT = "DEPOSIT"
    LATE_FEE = "LATE_FEE"
    CHECK = "CHECK"
    EXPENSE_VOID = "EXPENSE_VOID"
    BILL = "BILL"
    VENDOR_CREDIT = "VENDOR_CREDIT"
    BILL_PAYMENT = "BILL_PAYMENT"
    PURCHASE_VOID = "PURCHASE_VOID"
    TRANSFER = "TRANSFER"
    SALES_TAX_PAYMENT = "SALES_TAX_PAYMENT"
    SALES_TAX_ADJUST = "SALES_TAX_ADJUST"
    CARD_CREDIT = "CARD_CREDIT"
    BANK_DEPOSIT = "BANK_DEPOSIT"
