"""
Import every model here so SQLAlchemy and Alembic can see all tables.
"""

from app.models.account import Account
from app.models.company import Company
from app.models.contact import Customer, Vendor
from app.models.expense import Expense, ExpenseLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.journal import JournalEntry, JournalLine
from app.models.payment import Payment
from app.models.product import Product
from app.models.recurring import RecurringSchedule
from app.models.user import User

__all__ = [
    "Account",
    "Company",
    "Customer",
    "Vendor",
    "Expense",
    "ExpenseLine",
    "Invoice",
    "InvoiceLine",
    "JournalEntry",
    "JournalLine",
    "Payment",
    "Product",
    "RecurringSchedule",
    "User",
]
