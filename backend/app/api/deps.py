"""
Dependency wiring (Dependency Inversion).

Routes never create repositories or services themselves. They ask for a
ready-made service through FastAPI's Depends(), and this file is the one
place that decides how each service is built.

The build_* functions take a database session and return a service.
The get_* functions are the FastAPI dependencies used by the routes.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import PasswordHasher, TokenService
from app.db.session import get_db
from app.integrations.email import build_email_sender
from app.integrations.payments import build_payment_processor
from app.models import User
from app.recurring.base import RecurringHandler
from app.recurring.journal_entry_handler import JournalEntryRecurringHandler
from app.recurring.sales_handlers import InvoiceRecurringHandler, SalesReceiptRecurringHandler
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository, UserRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.sales_repositories import (
    DepositRepository,
    EmailLogRepository,
    PaymentRepository,
    PaymentTermRepository,
    SalesDocumentRepository,
)
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.company_service import CompanyService
from app.services.contact_service import CustomerService, VendorService
from app.services.customer_documents_service import CustomerDocumentsService
from app.services.dashboard_service import DashboardService
from app.services.deposit_service import DepositService
from app.services.email_service import EmailService
from app.services.expense_service import ExpenseService
from app.services.invoice_service import InvoiceService
from app.services.journal_service import JournalService
from app.services.late_fee_service import LateFeeService
from app.services.ledger_service import LedgerService
from app.services.numbering import DocumentNumberService
from app.services.payment_service import PaymentService
from app.services.portal_service import PortalService
from app.services.product_service import ProductService
from app.services.recurring_service import RecurringService
from app.services.report_service import ReportService, build_default_reports
from app.services.sales_common import SalesLineBuilder
from app.services.sales_document_kinds import ALL_KINDS
from app.services.sales_document_service import SalesDocumentService
from app.services.statement_service import StatementService
from app.services.system_accounts import SystemAccounts
from app.services.terms_service import TermsService

bearer_scheme = HTTPBearer(auto_error=False)


# =====================================================================
# Building blocks
# =====================================================================

def build_ledger(db: Session) -> LedgerService:
    return LedgerService(JournalRepository(db), AccountRepository(db))


def build_system_accounts(db: Session) -> SystemAccounts:
    return SystemAccounts(AccountRepository(db))


def build_line_builder(db: Session) -> SalesLineBuilder:
    return SalesLineBuilder(ProductRepository(db), build_system_accounts(db))


def build_company_service(db: Session) -> CompanyService:
    return CompanyService(db, CompanyRepository(db), AccountRepository(db), settings)


def build_terms_service(db: Session) -> TermsService:
    return TermsService(db, PaymentTermRepository(db))


def build_payment_service(db: Session) -> PaymentService:
    return PaymentService(
        db,
        PaymentRepository(db),
        InvoiceRepository(db),
        CustomerRepository(db),
        SalesDocumentRepository(db),
        AccountRepository(db),
        build_system_accounts(db),
        build_ledger(db),
    )


def build_invoice_service(db: Session) -> InvoiceService:
    return InvoiceService(
        db,
        InvoiceRepository(db),
        CustomerRepository(db),
        CompanyRepository(db),
        JournalRepository(db),
        SalesDocumentRepository(db),
        build_line_builder(db),
        build_system_accounts(db),
        build_terms_service(db),
        build_ledger(db),
        build_payment_service(db),
    )


def build_sales_document_service(db: Session) -> SalesDocumentService:
    return SalesDocumentService(
        db,
        SalesDocumentRepository(db),
        CustomerRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_line_builder(db),
        build_system_accounts(db),
        DocumentNumberService(db, settings.invoice_number_start),
        build_ledger(db),
        ALL_KINDS,
    )


def build_statement_service(db: Session) -> StatementService:
    return StatementService(CustomerRepository(db), InvoiceRepository(db), PaymentRepository(db), SalesDocumentRepository(db))


def build_email_service(db: Session) -> EmailService:
    return EmailService(db, EmailLogRepository(db), build_email_sender(settings))


def build_customer_documents_service(db: Session) -> CustomerDocumentsService:
    return CustomerDocumentsService(
        db,
        CompanyRepository(db),
        InvoiceRepository(db),
        SalesDocumentRepository(db),
        build_statement_service(db),
        build_email_service(db),
        settings,
    )


def build_late_fee_service(db: Session) -> LateFeeService:
    return LateFeeService(db, InvoiceRepository(db), CompanyRepository(db), build_system_accounts(db), build_ledger(db))


def build_recurring_handlers(db: Session) -> list[RecurringHandler]:
    """Every transaction type that can recur. Add new handlers here."""
    journal_service = JournalService(db, JournalRepository(db), build_ledger(db))
    return [
        JournalEntryRecurringHandler(journal_service, build_ledger(db)),
        InvoiceRecurringHandler(build_invoice_service(db)),
        SalesReceiptRecurringHandler(build_sales_document_service(db)),
    ]


def build_recurring_service(db: Session) -> RecurringService:
    return RecurringService(db, RecurringRepository(db), build_recurring_handlers(db))


# =====================================================================
# Auth
# =====================================================================

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


# =====================================================================
# Services used by the routes
# =====================================================================

def get_company_service(db: Session = Depends(get_db)) -> CompanyService:
    return build_company_service(db)


def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(db, AccountRepository(db), JournalRepository(db))


def get_customer_service(db: Session = Depends(get_db)) -> CustomerService:
    return CustomerService(
        db,
        CustomerRepository(db),
        InvoiceRepository(db),
        SalesDocumentRepository(db),
        PaymentRepository(db),
        PaymentTermRepository(db),
    )


def get_vendor_service(db: Session = Depends(get_db)) -> VendorService:
    return VendorService(db, VendorRepository(db))


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db, ProductRepository(db), AccountRepository(db))


def get_terms_service(db: Session = Depends(get_db)) -> TermsService:
    return build_terms_service(db)


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return build_invoice_service(db)


def get_sales_document_service(db: Session = Depends(get_db)) -> SalesDocumentService:
    return build_sales_document_service(db)


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return build_payment_service(db)


def get_deposit_service(db: Session = Depends(get_db)) -> DepositService:
    return DepositService(
        db,
        DepositRepository(db),
        PaymentRepository(db),
        SalesDocumentRepository(db),
        AccountRepository(db),
        build_system_accounts(db),
        build_ledger(db),
    )


def get_late_fee_service(db: Session = Depends(get_db)) -> LateFeeService:
    return build_late_fee_service(db)


def get_statement_service(db: Session = Depends(get_db)) -> StatementService:
    return build_statement_service(db)


def get_customer_documents_service(db: Session = Depends(get_db)) -> CustomerDocumentsService:
    return build_customer_documents_service(db)


def get_email_service(db: Session = Depends(get_db)) -> EmailService:
    return build_email_service(db)


def get_portal_service(db: Session = Depends(get_db)) -> PortalService:
    return PortalService(
        InvoiceRepository(db),
        CompanyRepository(db),
        build_customer_documents_service(db),
        build_payment_processor(settings),
    )


def get_expense_service(db: Session = Depends(get_db)) -> ExpenseService:
    return ExpenseService(db, ExpenseRepository(db), VendorRepository(db), AccountRepository(db), build_ledger(db))


def get_journal_service(db: Session = Depends(get_db)) -> JournalService:
    return JournalService(db, JournalRepository(db), build_ledger(db))


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    reports = build_default_reports(JournalRepository(db), InvoiceRepository(db))
    return ReportService(reports)


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(JournalRepository(db), InvoiceRepository(db))


def get_recurring_service(db: Session = Depends(get_db)) -> RecurringService:
    return build_recurring_service(db)
