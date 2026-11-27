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
from app.models.health import HealthDismissal
from app.models.integration import ApiKey, Webhook, WebhookDelivery
from app.models.inventory import (
    BundleComponent,
    InventoryAdjustment,
    InventoryAdjustmentLine,
    InventoryLayer,
    InventoryMovement,
    InventoryUse,
    PriceRule,
    ProductCategory,
)
from app.models.invoice import Invoice, InvoiceLine
from app.models.journal import JournalEntry, JournalLine
from app.models.mileage import Trip
from app.models.payment import CreditApplication, Payment, PaymentApplication
from app.models.payroll import (
    Employee,
    EmployeePayItem,
    PayItem,
    Paycheck,
    PaycheckLine,
    PaySchedule,
    PayrollLiabilityPayment,
    PayrollRun,
    TimeEntry,
)
from app.models.platform import AuditLog, CompanyMember, Currency, ExchangeRate, Invitation
from app.models.product import Product
from app.models.purchase import (
    BillPayment,
    BillPaymentApplication,
    PurchaseDocument,
    PurchaseDocumentLine,
    VendorCreditUse,
)
from app.models.recurring import RecurringSchedule
from app.models.saved_report import ReportSchedule, SavedReport
from app.models.sales_document import SalesDocument, SalesDocumentLine
from app.models.tax import SalesTaxAdjustment, SalesTaxLine, SalesTaxPayment, TaxAgency, TaxCode, TaxCodeRate, TaxRate
from app.models.tracking import Budget, BudgetLine, Location, Project, Tag, TrackingClass
from app.models.terms import NumberSequence, PaymentTerm
from app.models.user import User

__all__ = [
    "ApiKey",
    "Webhook",
    "WebhookDelivery",
    "AuditLog",
    "CompanyMember",
    "Currency",
    "ExchangeRate",
    "Invitation",
    "ReportSchedule",
    "SavedReport",
    "Budget",
    "BudgetLine",
    "Location",
    "Project",
    "Tag",
    "TrackingClass",
    "Employee",
    "EmployeePayItem",
    "PayItem",
    "Paycheck",
    "PaycheckLine",
    "PaySchedule",
    "PayrollLiabilityPayment",
    "PayrollRun",
    "TimeEntry",
    "BundleComponent",
    "InventoryAdjustment",
    "InventoryAdjustmentLine",
    "InventoryLayer",
    "InventoryMovement",
    "InventoryUse",
    "PriceRule",
    "ProductCategory",
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
    "HealthDismissal",
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
    "SalesTaxAdjustment",
    "SalesTaxLine",
    "SalesTaxPayment",
    "TaxAgency",
    "TaxCode",
    "TaxCodeRate",
    "TaxRate",
    "Transfer",
    "Trip",
    "User",
    "Vendor",
    "VendorCreditUse",
]
