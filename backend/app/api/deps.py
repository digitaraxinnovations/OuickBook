"""
Dependency wiring (Dependency Inversion).

Routes never create repositories or services themselves. They ask for a
ready-made service through FastAPI's Depends(), and this file is the one
place that decides how each service is built.

The build_* functions take a database session and return a service.
The get_* functions are the FastAPI dependencies used by the routes.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.request_context import remember_request
from app.core.security import PasswordHasher, TokenService
from app.db.session import get_db
from app.integrations.bank_feeds import build_bank_feed_provider
from app.integrations.email import build_email_sender
from app.integrations.exchange_rates import build_exchange_rate_provider
from app.integrations.payments import build_payment_processor
from app.integrations.payroll import PayrollProvider, build_payroll_provider
from app.integrations.tax_rates import TaxRateProvider, build_tax_rate_provider
from app.models import User
from app.recurring.base import RecurringHandler
from app.recurring.journal_entry_handler import JournalEntryRecurringHandler
from app.recurring.purchase_handlers import BillRecurringHandler, ExpenseRecurringHandler
from app.recurring.sales_handlers import InvoiceRecurringHandler, SalesReceiptRecurringHandler
from app.reports.balance_sheet import BalanceSheetComparisonReport, BalanceSheetReport
from app.reports.cash_flow import CashFlowReport
from app.reports.ledger_reports import (
    AccountQuickReport,
    BalanceSheetDetailReport,
    GeneralLedgerReport,
    JournalReport,
    LedgerQueries,
    TransactionListReport,
)
from app.reports.receivables_payables import (
    CollectionsReport,
    CustomerBalanceDetailReport,
    CustomerBalanceSummaryReport,
    OpenInvoicesReport,
    OpenItems,
    PayablesAgingDetailReport,
    PayablesAgingSummaryReport,
    ReceivablesAgingDetailReport,
    ReceivablesAgingSummaryReport,
    UnpaidBillsReport,
    VendorBalanceDetailReport,
    VendorBalanceSummaryReport,
)
from app.reports.report_data import LedgerFacts, ListNames, SourceNames
from app.reports.sales_expense_reports import ExpensesByVendorReport, SalesByCustomerReport, SalesByProductReport
from app.reports.inventory_valuation import InventoryValuationDetailReport, InventoryValuationSummaryReport
from app.reports.base import Report
from app.reports.payroll_summary import PayrollSummaryReport
from app.reports.profit_and_loss_by import (
    ProfitAndLossByClassReport,
    ProfitAndLossByLocationReport,
    ProfitAndLossByTagReport,
    ProjectProfitabilityReport,
)
from app.reports.profit_and_loss import (
    ProfitAndLossByCustomerReport,
    ProfitAndLossByMonthReport,
    ProfitAndLossComparisonReport,
    ProfitAndLossReport,
)
from app.reports.sales_tax_liability import SalesTaxLiabilityReport
from app.reports.tax_schedule import TaxScheduleReport
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
from app.repositories.inventory_repositories import (
    InventoryAdjustmentRepository,
    InventoryLayerRepository,
    InventoryMovementRepository,
    InventoryUseRepository,
    PriceRuleRepository,
    ProductCategoryRepository,
)
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
from app.repositories.payroll_repositories import (
    EmployeeRepository,
    LiabilityPaymentRepository,
    PayItemRepository,
    PayrollRunRepository,
    PayScheduleRepository,
    TimeEntryRepository,
)
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.tax_repositories import (
    SalesTaxAdjustmentRepository,
    SalesTaxLineRepository,
    SalesTaxPaymentRepository,
    TaxAgencyRepository,
    TaxCodeRepository,
    TaxRateRepository,
)
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
from app.services.closing_date import ClosingDateGuard
from app.services.currency_service import CurrencyService
from app.services.data_transfer_service import DataTransferService, build_transfers
from app.services.integration_service import IntegrationService
from app.services.membership_service import MembershipService
from app.services.notification_service import NotificationService
from app.services.platform_service import AuditLogService, RecentService, SearchService, SettingsService
from app.services.saved_report_service import SavedReportService
from app.services.catalog_service import CatalogService
from app.services.inventory_adjustment_service import InventoryAdjustmentService
from app.services.inventory_service import InventoryService
from app.services.paycheck_calculator import PaycheckCalculator
from app.services.payroll_liability_service import PayrollLiabilityService
from app.services.payroll_run_service import PayrollRunService
from app.services.payroll_setup_service import PayrollSetupService
from app.services.product_import_service import ProductImportService
from app.services.time_service import TimeService
from app.services.sales_common import SalesLineBuilder
from app.services.sales_tax import SalesTaxCalculator
from app.services.tax_service import TaxService
from app.services.sales_document_kinds import ALL_KINDS
from app.services.sales_document_service import SalesDocumentService
from app.services.statement_service import StatementService
from app.services.system_accounts import SystemAccounts
from app.services.terms_service import TermsService
from app.services.transfer_service import TransferService
from app.repositories.tracking_repositories import BudgetRepository, DimensionQueries, LocationRepository, ProjectRepository, TagRepository, TrackingClassRepository
from app.services.budget_service import BudgetService
from app.services.project_service import ProjectService
from app.services.tracking_service import TrackingService

bearer_scheme = HTTPBearer(auto_error=False)


# =====================================================================
# Building blocks
# =====================================================================

def build_ledger(db: Session) -> LedgerService:
    guard = ClosingDateGuard(CompanyRepository(db), PasswordHasher(settings.bcrypt_rounds))
    return LedgerService(JournalRepository(db), AccountRepository(db), guard)


def build_system_accounts(db: Session) -> SystemAccounts:
    return SystemAccounts(AccountRepository(db))


def build_line_builder(db: Session) -> SalesLineBuilder:
    return SalesLineBuilder(ProductRepository(db), build_system_accounts(db))


def build_tracking(db: Session) -> TrackingService:
    return TrackingService(
        db, TrackingClassRepository(db), LocationRepository(db), TagRepository(db), ProjectRepository(db), CustomerRepository(db)
    )


def build_inventory(db: Session) -> InventoryService:
    return InventoryService(
        ProductRepository(db),
        InventoryLayerRepository(db),
        InventoryUseRepository(db),
        InventoryMovementRepository(db),
        build_system_accounts(db),
    )


def build_product_service(db: Session) -> ProductService:
    return ProductService(
        db,
        ProductRepository(db),
        AccountRepository(db),
        ProductCategoryRepository(db),
        InventoryMovementRepository(db),
        build_system_accounts(db),
        build_inventory(db),
        build_ledger(db),
    )


def build_catalog_service(db: Session) -> CatalogService:
    return CatalogService(db, ProductCategoryRepository(db), PriceRuleRepository(db), ProductRepository(db), CustomerRepository(db))


def build_tax_calculator(db: Session) -> SalesTaxCalculator:
    return SalesTaxCalculator(TaxCodeRepository(db), SalesTaxLineRepository(db))


def build_tax_service(db: Session) -> TaxService:
    return TaxService(
        db,
        TaxAgencyRepository(db),
        TaxRateRepository(db),
        TaxCodeRepository(db),
        SalesTaxLineRepository(db),
        SalesTaxPaymentRepository(db),
        SalesTaxAdjustmentRepository(db),
        AccountRepository(db),
        build_system_accounts(db),
        build_ledger(db),
    )


def build_company_service(db: Session) -> CompanyService:
    return CompanyService(db, CompanyRepository(db), AccountRepository(db), settings)


def build_terms_service(db: Session) -> TermsService:
    return TermsService(db, PaymentTermRepository(db))


def build_currency_service(db: Session) -> CurrencyService:
    return CurrencyService(db, CompanyRepository(db), build_exchange_rate_provider(settings))


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
        build_currency_service(db),
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
        build_tax_calculator(db),
        build_currency_service(db),
        build_inventory(db),
        TimeEntryRepository(db),
        build_tracking(db),
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
        build_tax_calculator(db),
        build_currency_service(db),
        build_inventory(db),
        build_tracking(db),
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
        build_inventory(db),
        build_tracking(db),
        build_currency_service(db),
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
        build_inventory(db),
        build_tracking(db),
        build_currency_service(db),
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
    names = SourceNames(db)
    facts = LedgerFacts(db, names)
    list_names = ListNames(db)
    ledger_queries = LedgerQueries(db)
    open_items = OpenItems(InvoiceRepository(db), PurchaseDocumentRepository(db))
    return [
        # Business overview
        ProfitAndLossReport(facts, list_names),
        ProfitAndLossByMonthReport(facts, list_names),
        ProfitAndLossByCustomerReport(facts, list_names),
        ProfitAndLossComparisonReport(facts, list_names),
        BalanceSheetReport(JournalRepository(db)),
        BalanceSheetComparisonReport(JournalRepository(db)),
        BalanceSheetDetailReport(ledger_queries, names, JournalRepository(db)),
        CashFlowReport(JournalRepository(db)),
        # Who owes you
        ReceivablesAgingSummaryReport(open_items),
        ReceivablesAgingDetailReport(open_items),
        OpenInvoicesReport(open_items),
        CollectionsReport(open_items),
        CustomerBalanceSummaryReport(InvoiceRepository(db), SalesDocumentRepository(db), PaymentRepository(db), list_names),
        CustomerBalanceDetailReport(open_items),
        # Sales and customers
        SalesByCustomerReport(facts, list_names),
        SalesByProductReport(db),
        # What you owe
        PayablesAgingSummaryReport(open_items),
        PayablesAgingDetailReport(open_items),
        UnpaidBillsReport(open_items),
        VendorBalanceSummaryReport(PurchaseDocumentRepository(db), list_names),
        VendorBalanceDetailReport(open_items),
        # Expenses and vendors
        ExpensesByVendorReport(facts, list_names),
        # For my accountant
        TrialBalanceReport(JournalRepository(db)),
        GeneralLedgerReport(ledger_queries, names, JournalRepository(db)),
        AccountQuickReport(ledger_queries, names, JournalRepository(db)),
        JournalReport(ledger_queries, names),
        TransactionListReport(ledger_queries, names),
        Vendor1099Report(VendorRepository(db), ExpenseQueries(db), BillPaymentRepository(db), settings.form_1099_threshold),
        SalesTaxLiabilityReport(
            TaxAgencyRepository(db), SalesTaxLineRepository(db), SalesTaxPaymentRepository(db), SalesTaxAdjustmentRepository(db)
        ),
        TaxScheduleReport(JournalRepository(db)),
        InventoryValuationSummaryReport(ProductRepository(db), InventoryMovementRepository(db)),
        InventoryValuationDetailReport(ProductRepository(db), InventoryMovementRepository(db)),
        PayrollSummaryReport(PayrollRunRepository(db)),
        ProfitAndLossByClassReport(DimensionQueries(db), AccountRepository(db), TrackingClassRepository(db)),
        ProfitAndLossByLocationReport(DimensionQueries(db), AccountRepository(db), LocationRepository(db)),
        ProfitAndLossByTagReport(DimensionQueries(db), AccountRepository(db), TagRepository(db)),
        ProjectProfitabilityReport(DimensionQueries(db), AccountRepository(db), ProjectRepository(db)),
    ]


def build_late_fee_service(db: Session) -> LateFeeService:
    return LateFeeService(db, InvoiceRepository(db), CompanyRepository(db), build_system_accounts(db), build_ledger(db))


def build_recurring_handlers(db: Session) -> list[RecurringHandler]:
    """Every transaction type that can recur. Add new handlers here."""
    journal_service = JournalService(db, JournalRepository(db), build_ledger(db), build_tracking(db))
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


def build_membership_service(db: Session) -> MembershipService:
    return MembershipService(
        db,
        settings,
        UserRepository(db),
        CompanyRepository(db),
        build_company_service(db),
        build_email_service(db),
        PasswordHasher(settings.bcrypt_rounds),
        TokenService(settings.jwt_secret_key, settings.jwt_algorithm, settings.access_token_expire_minutes),
    )


def get_membership_service(db: Session = Depends(get_db)) -> MembershipService:
    return build_membership_service(db)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    memberships: MembershipService = Depends(get_membership_service),
) -> User:
    """
    The signed-in user, after checking their role allows this request
    (see core/permissions.py). Also remembers who they are for the audit log,
    and the closing password if they typed one (X-Closing-Password header).
    """
    if credentials is None:
        raise AuthenticationError("Please sign in.")
    user = auth_service.get_user_from_token(credentials.credentials)
    memberships.check_access(user, request.url.path, request.method)
    remember_request(memberships.session, user.id, request.headers.get("X-Closing-Password"))
    return user


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
        TaxCodeRepository(db),
        build_currency_service(db),
    )


def get_vendor_service(db: Session = Depends(get_db)) -> VendorService:
    return VendorService(db, VendorRepository(db), PurchaseDocumentRepository(db), PaymentTermRepository(db), build_currency_service(db))


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return build_product_service(db)


def get_product_import_service(db: Session = Depends(get_db)) -> ProductImportService:
    return ProductImportService(db, ProductRepository(db), ProductCategoryRepository(db), build_product_service(db), build_catalog_service(db))


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return build_catalog_service(db)


def get_inventory_adjustment_service(db: Session = Depends(get_db)) -> InventoryAdjustmentService:
    return InventoryAdjustmentService(
        db,
        InventoryAdjustmentRepository(db),
        ProductRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_system_accounts(db),
        DocumentNumberService(db, 1),
        build_inventory(db),
        build_ledger(db),
    )


def get_inventory_history(db: Session = Depends(get_db)) -> InventoryMovementRepository:
    return InventoryMovementRepository(db)


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
        build_currency_service(db),
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
    return JournalService(db, JournalRepository(db), build_ledger(db), build_tracking(db))


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(build_reports(db))


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(JournalRepository(db), InvoiceRepository(db), PurchaseDocumentRepository(db))


def get_recurring_service(db: Session = Depends(get_db)) -> RecurringService:
    return build_recurring_service(db)


# =====================================================================
# Banking
# =====================================================================

def get_tax_service(db: Session = Depends(get_db)) -> TaxService:
    return build_tax_service(db)


def get_tax_rate_provider() -> TaxRateProvider:
    return build_tax_rate_provider(settings)


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


# ---------- payroll and time ----------


def get_payroll_provider() -> PayrollProvider:
    return build_payroll_provider(settings)


def get_payroll_setup_service(db: Session = Depends(get_db)) -> PayrollSetupService:
    return PayrollSetupService(db, PayScheduleRepository(db), PayItemRepository(db), EmployeeRepository(db), AccountRepository(db))


def get_payroll_run_service(db: Session = Depends(get_db)) -> PayrollRunService:
    calculator = PaycheckCalculator(build_payroll_provider(settings), settings.payroll_overtime_multiplier)
    return PayrollRunService(
        db,
        PayrollRunRepository(db),
        PayScheduleRepository(db),
        EmployeeRepository(db),
        PayItemRepository(db),
        TimeEntryRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_system_accounts(db),
        build_check_numbers(db),
        calculator,
        build_ledger(db),
    )


def get_payroll_liability_service(db: Session = Depends(get_db)) -> PayrollLiabilityService:
    return PayrollLiabilityService(
        db,
        LiabilityPaymentRepository(db),
        PayItemRepository(db),
        PayrollRunRepository(db),
        AccountRepository(db),
        JournalRepository(db),
        build_system_accounts(db),
        build_ledger(db),
    )


def get_time_service(db: Session = Depends(get_db)) -> TimeService:
    return TimeService(
        db, TimeEntryRepository(db), EmployeeRepository(db), VendorRepository(db), CustomerRepository(db), ProductRepository(db), ProjectRepository(db)
    )


def get_company_repository(db: Session = Depends(get_db)) -> CompanyRepository:
    return CompanyRepository(db)


# ---------- classes, locations, projects, budgets ----------


def get_tracking_service(db: Session = Depends(get_db)) -> TrackingService:
    return build_tracking(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(ProjectRepository(db), CustomerRepository(db), build_tracking(db))


def get_budget_service(db: Session = Depends(get_db)) -> BudgetService:
    return BudgetService(
        db, BudgetRepository(db), AccountRepository(db), TrackingClassRepository(db), LocationRepository(db), DimensionQueries(db)
    )


# ---------- saved reports, export, schedules ----------


def build_saved_report_service(db: Session) -> SavedReportService:
    return SavedReportService(db, ReportService(build_reports(db)), CompanyRepository(db), build_email_service(db))


def get_saved_report_service(db: Session = Depends(get_db)) -> SavedReportService:
    return build_saved_report_service(db)


# ---------- settings, currencies, audit log, search, import ----------


def get_settings_service(db: Session = Depends(get_db)) -> SettingsService:
    return SettingsService(db, CompanyRepository(db), PasswordHasher(settings.bcrypt_rounds))


def get_currency_service(db: Session = Depends(get_db)) -> CurrencyService:
    return build_currency_service(db)


def get_audit_log_service(db: Session = Depends(get_db)) -> AuditLogService:
    return AuditLogService(db)


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


def get_recent_service(db: Session = Depends(get_db)) -> RecentService:
    return RecentService(db, SourceNames(db))


def get_data_transfer_service(db: Session = Depends(get_db)) -> DataTransferService:
    transfers = build_transfers(
        CustomerRepository(db),
        get_customer_service(db),
        VendorRepository(db),
        get_vendor_service(db),
        AccountRepository(db),
        get_account_service(db),
        JournalRepository(db),
        get_journal_service(db),
        get_product_import_service(db),
    )
    return DataTransferService(db, transfers)


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db, build_tax_service(db))


def get_integration_service(db: Session = Depends(get_db)) -> IntegrationService:
    return IntegrationService(db)

