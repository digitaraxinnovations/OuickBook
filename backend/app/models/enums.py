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


class JournalSource(str, Enum):
    """Which screen created a journal entry."""

    MANUAL = "MANUAL"
    INVOICE = "INVOICE"
    INVOICE_VOID = "INVOICE_VOID"
    PAYMENT = "PAYMENT"
    EXPENSE = "EXPENSE"
