"""
Dependency wiring (Dependency Inversion).

Routes never create repositories or services themselves. They ask for a
ready-made service through FastAPI's Depends(), and this file is the one
place that decides how each service is built.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import PasswordHasher, TokenService
from app.db.session import get_db
from app.models import User
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository, UserRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.recurring_repository import RecurringRepository
from app.recurring.base import RecurringHandler
from app.recurring.journal_entry_handler import JournalEntryRecurringHandler
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.company_service import CompanyService
from app.services.contact_service import CustomerService, VendorService
from app.services.dashboard_service import DashboardService
from app.services.expense_service import ExpenseService
from app.services.invoice_service import InvoiceService
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService
from app.services.recurring_service import RecurringService
from app.services.report_service import ReportService, build_default_reports

bearer_scheme = HTTPBearer(auto_error=False)


# ---------- building blocks ----------

def build_ledger(db: Session) -> LedgerService:
    return LedgerService(JournalRepository(db), AccountRepository(db))


def build_company_service(db: Session) -> CompanyService:
    return CompanyService(db, CompanyRepository(db), AccountRepository(db), settings)


# ---------- auth ----------

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(
        db,
        UserRepository(db),
        build_company_service(db),
        PasswordHasher(settings.bcrypt_rounds),
        TokenService(settings.jwt_secret_key, settings.jwt_algorithm, settings.access_token_expire_minutes),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None:
        raise AuthenticationError("Please sign in.")
    return auth_service.get_user_from_token(credentials.credentials)


# ---------- services used by the routes ----------

def get_company_service(db: Session = Depends(get_db)) -> CompanyService:
    return build_company_service(db)


def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(db, AccountRepository(db), JournalRepository(db))


def get_customer_service(db: Session = Depends(get_db)) -> CustomerService:
    return CustomerService(db, CustomerRepository(db), InvoiceRepository(db))


def get_vendor_service(db: Session = Depends(get_db)) -> VendorService:
    return VendorService(db, VendorRepository(db))


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db, ProductRepository(db), AccountRepository(db))


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(
        db,
        InvoiceRepository(db),
        CustomerRepository(db),
        ProductRepository(db),
        AccountRepository(db),
        CompanyRepository(db),
        JournalRepository(db),
        build_ledger(db),
    )


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return PaymentService(db, PaymentRepository(db), InvoiceRepository(db), AccountRepository(db), build_ledger(db))


def get_expense_service(db: Session = Depends(get_db)) -> ExpenseService:
    return ExpenseService(db, ExpenseRepository(db), VendorRepository(db), AccountRepository(db), build_ledger(db))


def get_journal_service(db: Session = Depends(get_db)) -> JournalService:
    return JournalService(db, JournalRepository(db), build_ledger(db))


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    reports = build_default_reports(JournalRepository(db), InvoiceRepository(db))
    return ReportService(reports)


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(JournalRepository(db), InvoiceRepository(db))


# ---------- recurring transactions ----------

def build_recurring_handlers(db: Session) -> list[RecurringHandler]:
    """Every transaction type that can recur. Add new handlers here."""
    journal_service = JournalService(db, JournalRepository(db), build_ledger(db))
    return [
        JournalEntryRecurringHandler(journal_service, build_ledger(db)),
    ]


def build_recurring_service(db: Session) -> RecurringService:
    return RecurringService(db, RecurringRepository(db), build_recurring_handlers(db))


def get_recurring_service(db: Session = Depends(get_db)) -> RecurringService:
    return build_recurring_service(db)
