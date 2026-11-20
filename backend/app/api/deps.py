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
from app.integrations.bank_feeds import build_bank_feed_provider
from app.integrations.email import build_email_sender
from app.integrations.payments import build_payment_processor
from app.models import User
from app.recurring.base import RecurringHandler
from app.recurring.journal_entry_handler import JournalEntryRecurringHandler
from app.recurring.purchase_handlers import BillRecurringHandler, ExpenseRecurringHandler
from app.recurring.sales_handlers import InvoiceRecurringHandler, SalesReceiptRecurringHandler
from app.reports.balance_sheet import BalanceSheetReport
from app.reports.base import Report
from app.reports.payables_aging import PayablesAgingReport
from app.reports.profit_and_loss import ProfitAndLossReport
from app.reports.receivables_aging import ReceivablesAgingReport
from app.reports.trial_balance import TrialBalanceReport
from app.reports.vendor_1099 import Vendor1099Report
from app.repositories.account_repository import AccountRepository
from app.repositories.banking_repositories import (
    BankRuleRepository,
    BankTransactionRepository,
    ReconciliationRepository,
    RegisterQueries,
    TransferRepository,
)
from app.repositories.company_repository import CompanyRepository, UserRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.purchase_repositories import (
    AttachmentRepository,
    BillPaymentRepository,
    ExpenseQueries,
    PurchaseDocumentRepository,
    TripRepository,
)
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.sales_repositories import (
    DepositRepository,
    EmailLogRepository,
    PaymentRepository,
    PaymentTermRepository,
    SalesDocumentRepository,
)
from app.services.account_service import AccountService
from app.services.attachment_service import AttachmentService
from app.services.auth_service import AuthService
from app.services.bank_import_service import BankImportService
from app.services.bank_review_service import BankReviewService
from app.services.bank_rule_service import BankRuleService
from app.services.bill_payment_service import BillPaymentService
from app.services.check_numbers import CheckNumberService
from app.services.check_printing_service import CheckPrintingService
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
from app.services.mileage_service import MileageService
from app.services.numbering import DocumentNumberService
from app.services.payment_service import PaymentService
from app.services.portal_service import PortalService
from app.services.product_service import ProductService
from app.services.purchase_document_service import PurchaseDocumentService
from app.services.purchase_kinds import ALL_PURCHASE_KINDS
from app.services.reconciliation_service import ReconciliationService
from app.services.recurring_service import RecurringService
from app.services.report_service import ReportService
from app.services.sales_common import SalesLineBuilder
from app.services.sales_document_kinds import ALL_KINDS
from app.services.sales_document_service import SalesDocumentService
from app.services.statement_service import StatementService
from app.services.system_accounts import SystemAccounts
from app.services.terms_service import TermsService
from app.services.transfer_service import TransferService

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


def build_check_numbers(db: Session) -> CheckNumberService:
    return CheckNumberService(DocumentNumberService(db, settings.first_check_number))


def build_expense_service(db: Session) -> ExpenseService:
    return ExpenseService(
        db,
        ExpenseRepository(db),
        VendorRepository(db),
        CustomerRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_check_numbers(db),
        build_ledger(db),
    )


def build_purchase_service(db: Session) -> PurchaseDocumentService:
    return PurchaseDocumentService(
        db,
        PurchaseDocumentRepository(db),
        VendorRepository(db),
        CustomerRepository(db),
        AccountRepository(db),
        CompanyRepository(db),
        PaymentTermRepository(db),
        JournalRepository(db),
        build_system_accounts(db),
        DocumentNumberService(db, settings.invoice_number_start),
        build_ledger(db),
        ALL_PURCHASE_KINDS,
    )


def build_deposit_service(db: Session) -> DepositService:
    return DepositService(
        db,
        DepositRepository(db),
        PaymentRepository(db),
        SalesDocumentRepository(db),
        AccountRepository(db),
        build_system_accounts(db),
        build_ledger(db),
    )


def build_transfer_service(db: Session) -> TransferService:
    return TransferService(db, TransferRepository(db), AccountRepository(db), JournalRepository(db), build_ledger(db))


def build_bank_review_service(db: Session) -> BankReviewService:
    return BankReviewService(
        db,
        BankTransactionRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        RegisterQueries(db),
        build_expense_service(db),
        build_deposit_service(db),
        build_transfer_service(db),
        settings.bank_match_days,
    )


def build_reports(db: Session) -> list[Report]:
    """Every report in the Reports page. Add new reports here."""
    return [
        ProfitAndLossReport(JournalRepository(db)),
        BalanceSheetReport(JournalRepository(db)),
        TrialBalanceReport(JournalRepository(db)),
        ReceivablesAgingReport(InvoiceRepository(db)),
        PayablesAgingReport(PurchaseDocumentRepository(db)),
        Vendor1099Report(VendorRepository(db), ExpenseQueries(db), BillPaymentRepository(db), settings.form_1099_threshold),
    ]


def build_late_fee_service(db: Session) -> LateFeeService:
    return LateFeeService(db, InvoiceRepository(db), CompanyRepository(db), build_system_accounts(db), build_ledger(db))


def build_recurring_handlers(db: Session) -> list[RecurringHandler]:
    """Every transaction type that can recur. Add new handlers here."""
    journal_service = JournalService(db, JournalRepository(db), build_ledger(db))
    return [
        JournalEntryRecurringHandler(journal_service, build_ledger(db)),
        InvoiceRecurringHandler(build_invoice_service(db)),
        SalesReceiptRecurringHandler(build_sales_document_service(db)),
        BillRecurringHandler(build_purchase_service(db)),
        ExpenseRecurringHandler(build_expense_service(db)),
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
    return VendorService(db, VendorRepository(db), PurchaseDocumentRepository(db), PaymentTermRepository(db))


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
    return build_deposit_service(db)


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
    return build_expense_service(db)


def get_purchase_service(db: Session = Depends(get_db)) -> PurchaseDocumentService:
    return build_purchase_service(db)


def get_bill_payment_service(db: Session = Depends(get_db)) -> BillPaymentService:
    return BillPaymentService(
        db,
        BillPaymentRepository(db),
        PurchaseDocumentRepository(db),
        VendorRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_system_accounts(db),
        build_check_numbers(db),
        build_ledger(db),
    )


def get_check_printing_service(db: Session = Depends(get_db)) -> CheckPrintingService:
    return CheckPrintingService(
        db,
        ExpenseRepository(db),
        ExpenseQueries(db),
        BillPaymentRepository(db),
        AccountRepository(db),
        CompanyRepository(db),
        build_check_numbers(db),
    )


def get_attachment_service(db: Session = Depends(get_db)) -> AttachmentService:
    return AttachmentService(db, AttachmentRepository(db), settings.max_attachment_bytes)


def get_mileage_service(db: Session = Depends(get_db)) -> MileageService:
    return MileageService(db, TripRepository(db), CompanyRepository(db))


def get_journal_service(db: Session = Depends(get_db)) -> JournalService:
    return JournalService(db, JournalRepository(db), build_ledger(db))


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(build_reports(db))


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(JournalRepository(db), InvoiceRepository(db), PurchaseDocumentRepository(db))


def get_recurring_service(db: Session = Depends(get_db)) -> RecurringService:
    return build_recurring_service(db)


# =====================================================================
# Banking
# =====================================================================

def get_transfer_service(db: Session = Depends(get_db)) -> TransferService:
    return build_transfer_service(db)


def get_bank_review_service(db: Session = Depends(get_db)) -> BankReviewService:
    return build_bank_review_service(db)


def get_bank_import_service(db: Session = Depends(get_db)) -> BankImportService:
    return BankImportService(
        db,
        BankTransactionRepository(db),
        BankRuleRepository(db),
        build_bank_review_service(db),
        build_bank_feed_provider(settings),
    )


def get_bank_rule_service(db: Session = Depends(get_db)) -> BankRuleService:
    return BankRuleService(db, BankRuleRepository(db), AccountRepository(db), VendorRepository(db))


def get_reconciliation_service(db: Session = Depends(get_db)) -> ReconciliationService:
    return ReconciliationService(db, ReconciliationRepository(db), RegisterQueries(db), build_bank_review_service(db))
