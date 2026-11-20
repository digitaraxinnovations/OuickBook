"""
Company-wide services:

- SettingsService:  advanced settings (fiscal year, accounting method,
                    closing date and password, multicurrency) and expense settings.
- AuditLogService:  reading the audit log (it is written automatically, see db/audit.py).
- SearchService:    one search box for customers, vendors, transactions, accounts...
- RecentService:    the latest transactions, newest first.
"""

from datetime import date

from sqlalchemy import String, cast, func, or_, select

from app.core.money import ZERO
from app.core.security import PasswordHasher
from app.models import (
    Account,
    AuditLog,
    Company,
    Customer,
    Employee,
    Expense,
    Invoice,
    JournalEntry,
    Product,
    PurchaseDocument,
    SalesDocument,
    User,
    Vendor,
)
from app.models.enums import JournalSource
from app.reports.report_data import SourceNames
from app.repositories.company_repository import CompanyRepository
from app.schemas.platform import AdvancedSettingsRead, AdvancedSettingsUpdate, AuditLogRead, RecentTransaction, SearchResult
from app.services.base import BaseService

SEARCH_LIMIT = 8


class SettingsService(BaseService):
    def __init__(self, session, company_repository: CompanyRepository, password_hasher: PasswordHasher):
        super().__init__(session)
        self.company_repository = company_repository
        self.password_hasher = password_hasher

    def get(self, company_id: int) -> AdvancedSettingsRead:
        company = self.company_repository.get(company_id)
        return self.to_read(company)

    def update(self, company_id: int, data: AdvancedSettingsUpdate) -> AdvancedSettingsRead:
        company = self.company_repository.get(company_id)
        company.fiscal_year_start_month = data.fiscal_year_start_month
        company.accounting_method = data.accounting_method
        company.closing_date = data.closing_date
        company.bill_terms_days = data.bill_terms_days
        if company.multicurrency_enabled and not data.multicurrency_enabled:
            from app.core.exceptions import BusinessRuleError

            raise BusinessRuleError("Multicurrency cannot be turned off once it is on.")
        company.multicurrency_enabled = data.multicurrency_enabled
        if data.remove_closing_password:
            company.closing_password_hash = None
        elif data.closing_password:
            company.closing_password_hash = self.password_hasher.hash(data.closing_password)
        self.commit()
        return self.to_read(company)

    def to_read(self, company: Company) -> AdvancedSettingsRead:
        return AdvancedSettingsRead(
            fiscal_year_start_month=company.fiscal_year_start_month,
            accounting_method=company.accounting_method,
            closing_date=company.closing_date,
            has_closing_password=company.closing_password_hash is not None,
            multicurrency_enabled=company.multicurrency_enabled,
            currency=company.currency,
            bill_terms_days=company.bill_terms_days,
        )


class AuditLogService:
    def __init__(self, session):
        self.session = session

    def list(
        self,
        company_id: int,
        start: date | None = None,
        end: date | None = None,
        user_id: int | None = None,
        entity_type: str | None = None,
        limit: int = 200,
    ) -> list[AuditLogRead]:
        query = select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.user_id).where(AuditLog.company_id == company_id)
        if start is not None:
            query = query.where(func.date(AuditLog.created_at) >= start)
        if end is not None:
            query = query.where(func.date(AuditLog.created_at) <= end)
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
        result = []
        for entry, user_name in self.session.execute(query):
            result.append(
                AuditLogRead(
                    id=entry.id,
                    user_name=user_name or "System (daily job)",
                    action=entry.action,
                    entity_type=entry.entity_type,
                    entity_id=entry.entity_id,
                    summary=entry.summary,
                    changes=entry.changes,
                    created_at=entry.created_at,
                )
            )
        return result


class SearchService:
    """Finds records whose name or number contains the text typed."""

    def __init__(self, session):
        self.session = session

    def search(self, company_id: int, text: str) -> list[SearchResult]:
        term = text.strip()
        if len(term) < 2:
            return []
        like = f"%{term.lower()}%"
        results = []

        def lower(column):
            return func.lower(cast(column, String))

        for customer in self.find(Customer, company_id, or_(lower(Customer.display_name).like(like), lower(Customer.email).like(like))):
            results.append(SearchResult(kind="Customer", title=customer.display_name, subtitle=customer.email or "", href=f"/sales/customers/{customer.id}"))
        for vendor in self.find(Vendor, company_id, lower(Vendor.display_name).like(like)):
            results.append(SearchResult(kind="Vendor", title=vendor.display_name, subtitle=vendor.email or "", href=f"/expenses/vendors/{vendor.id}"))
        for employee in self.find(Employee, company_id, lower(Employee.display_name).like(like)):
            results.append(SearchResult(kind="Employee", title=employee.display_name, subtitle="", href="/payroll/employees"))
        for invoice in self.find(Invoice, company_id, or_(lower(Invoice.invoice_number).like(like), lower(Invoice.memo).like(like))):
            results.append(
                SearchResult(kind="Invoice", title=f"Invoice {invoice.invoice_number}", subtitle=f"{invoice.customer.display_name} · {invoice.total}", href=f"/sales/invoices/{invoice.id}")
            )
        for document in self.find(SalesDocument, company_id, lower(SalesDocument.doc_number).like(like)):
            kind = document.doc_type.value.replace("_", " ").title()
            results.append(SearchResult(kind=kind, title=f"{kind} {document.doc_number}", subtitle=document.customer.display_name, href=f"/sales/forms/{self.sales_slug(document)}/{document.id}"))
        for bill in self.find(PurchaseDocument, company_id, lower(PurchaseDocument.doc_number).like(like)):
            kind = bill.doc_type.value.replace("_", " ").title()
            results.append(SearchResult(kind=kind, title=f"{kind} {bill.doc_number}", subtitle=bill.vendor.display_name, href=f"/expenses/forms/{self.purchase_slug(bill)}/{bill.id}"))
        for expense in self.find(Expense, company_id, or_(lower(Expense.reference_no).like(like), lower(Expense.memo).like(like), lower(Expense.check_number).like(like))):
            results.append(SearchResult(kind="Expense", title=expense.memo or expense.reference_no or f"Expense #{expense.id}", subtitle=str(expense.total), href=f"/expenses/{expense.id}"))
        for product in self.find(Product, company_id, or_(lower(Product.name).like(like), lower(Product.sku).like(like))):
            results.append(SearchResult(kind="Product", title=product.name, subtitle=product.sku or "", href="/sales/products"))
        for account in self.find(Account, company_id, lower(Account.name).like(like)):
            results.append(SearchResult(kind="Account", title=account.name, subtitle=account.account_type.value.title(), href=f"/reports/account-quickreport?account_id={account.id}"))
        # A number typed exactly matches transaction amounts too.
        results.extend(self.amount_matches(company_id, term))
        return results[:40]

    def find(self, model, company_id: int, condition) -> list:
        query = select(model).where(model.company_id == company_id, condition).limit(SEARCH_LIMIT)
        return list(self.session.scalars(query))

    def amount_matches(self, company_id: int, term: str) -> list[SearchResult]:
        try:
            amount = float(term.replace(",", "").replace("$", ""))
        except ValueError:
            return []
        results = []
        for invoice in self.find(Invoice, company_id, Invoice.total == amount):
            results.append(SearchResult(kind="Invoice", title=f"Invoice {invoice.invoice_number}", subtitle=f"{invoice.customer.display_name} · {invoice.total}", href=f"/sales/invoices/{invoice.id}"))
        for expense in self.find(Expense, company_id, Expense.total == amount):
            results.append(SearchResult(kind="Expense", title=expense.memo or f"Expense #{expense.id}", subtitle=str(expense.total), href=f"/expenses/{expense.id}"))
        for bill in self.find(PurchaseDocument, company_id, PurchaseDocument.total == amount):
            results.append(SearchResult(kind="Bill", title=f"{bill.doc_type.value.title()} {bill.doc_number or bill.id}", subtitle=bill.vendor.display_name, href=f"/expenses/forms/{self.purchase_slug(bill)}/{bill.id}"))
        return results

    @staticmethod
    def sales_slug(document) -> str:
        return document.doc_type.value.lower().replace("_", "-") + "s"

    @staticmethod
    def purchase_slug(document) -> str:
        return document.doc_type.value.lower().replace("_", "-") + "s"


class RecentService:
    """The latest transactions, with a link to open each one."""

    LINKS = {
        JournalSource.INVOICE: "/sales/invoices/{id}",
        JournalSource.EXPENSE: "/expenses/{id}",
        JournalSource.CHECK: "/expenses/{id}",
        JournalSource.CARD_CREDIT: "/expenses/{id}",
        JournalSource.MANUAL: None,
    }

    def __init__(self, session, names: SourceNames):
        self.session = session
        self.names = names

    def recent(self, company_id: int, limit: int = 10) -> list[RecentTransaction]:
        query = (
            select(JournalEntry)
            .where(JournalEntry.company_id == company_id, JournalEntry.reverses_entry_id.is_(None))
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .limit(limit)
        )
        entries = list(self.session.scalars(query))
        names = self.names.for_entries(company_id, entries)
        result = []
        for entry in entries:
            name = names[entry.id]
            pattern = self.LINKS.get(entry.source_type)
            href = pattern.format(id=entry.source_id) if pattern and entry.source_id else None
            result.append(
                RecentTransaction(
                    entry_date=entry.entry_date,
                    type_label=name.type_label,
                    number=name.number,
                    name=name.name or (entry.memo or ""),
                    amount=sum((line.debit for line in entry.lines), ZERO),
                    href=href,
                )
            )
        return result
