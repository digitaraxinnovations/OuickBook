"""
Import every model here so SQLAlchemy and Alembic can see all tables.
"""

from app.models.account import Account
from app.models.attachment import Attachment
from app.models.banking import BankRule, BankTransaction, Reconciliation, Transfer
from app.models.company import Company
from app.models.contact import Customer, Vendor
from app.models.deposit import BankDeposit, DepositLine
from app.models.email_log import EmailLog
from app.models.expense import Expense, ExpenseLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.journal import JournalEntry, JournalLine
from app.models.mileage import Trip
from app.models.payment import CreditApplication, Payment, PaymentApplication
from app.models.product import Product
from app.models.purchase import (
    BillPayment,
    BillPaymentApplication,
    PurchaseDocument,
    PurchaseDocumentLine,
    VendorCreditUse,
)
from app.models.recurring import RecurringSchedule
from app.models.sales_document import SalesDocument, SalesDocumentLine
from app.models.terms import NumberSequence, PaymentTerm
from app.models.user import User

__all__ = [
    "Account",
    "Attachment",
    "BankDeposit",
    "BankRule",
    "BankTransaction",
    "BillPayment",
    "BillPaymentApplication",
    "Company",
    "CreditApplication",
    "Customer",
    "DepositLine",
    "EmailLog",
    "Expense",
    "ExpenseLine",
    "Invoice",
    "InvoiceLine",
    "JournalEntry",
    "JournalLine",
    "NumberSequence",
    "Payment",
    "PaymentApplication",
    "PaymentTerm",
    "Product",
    "PurchaseDocument",
    "PurchaseDocumentLine",
    "Reconciliation",
    "RecurringSchedule",
    "SalesDocument",
    "SalesDocumentLine",
    "Transfer",
    "Trip",
    "User",
    "Vendor",
    "VendorCreditUse",
]
