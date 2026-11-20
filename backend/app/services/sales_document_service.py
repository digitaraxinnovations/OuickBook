"""
Estimates, sales receipts, credit memos, refund receipts, delayed charges
and delayed credits. The differences between them live in
sales_document_kinds.py; this class does what they have in common.
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import SalesDocument, SalesDocumentLine
from app.models.enums import JournalSource, SalesDocStatus, SalesDocType
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import CustomerRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.sales_repositories import SalesDocumentRepository
from app.schemas.sales_document import SalesDocumentCreate
from app.services.base import BaseService
from app.services.inventory_service import InventoryService, StockSource
from app.services.ledger_service import LedgerService
from app.services.numbering import DocumentNumberService
from app.services.sales_common import SalesLineBuilder, calculate_totals, income_ledger_lines
from app.services.sales_document_kinds import SalesDocumentKind
from app.services.sales_tax import SalesTaxCalculator
from app.services.system_accounts import SystemAccounts

ESTIMATE_STATUSES_USERS_CAN_SET = (SalesDocStatus.PENDING, SalesDocStatus.ACCEPTED, SalesDocStatus.REJECTED)
TAX_SOURCE = "SALES_DOCUMENT"


class SalesDocumentService(BaseService):
    def __init__(
        self,
        session,
        repository: SalesDocumentRepository,
        customer_repository: CustomerRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        line_builder: SalesLineBuilder,
        system_accounts: SystemAccounts,
        numbering: DocumentNumberService,
        ledger: LedgerService,
        kinds: list[SalesDocumentKind],
        tax_calculator: SalesTaxCalculator,
        inventory: InventoryService,
    ):
        super().__init__(session)
        self.repository = repository
        self.customer_repository = customer_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.line_builder = line_builder
        self.system_accounts = system_accounts
        self.numbering = numbering
        self.ledger = ledger
        self.tax_calculator = tax_calculator
        self.inventory = inventory
        self.kinds = {}
        for kind in kinds:
            self.kinds[kind.doc_type] = kind

    # ---------- reading ----------

    def list(self, company_id: int, doc_type=None, customer_id=None, status=None) -> list[SalesDocument]:
        return self.repository.list_filtered(company_id, doc_type, customer_id, status)

    def get(self, company_id: int, document_id: int) -> SalesDocument:
        document = self.repository.get(company_id, document_id)
        if document is None:
            raise NotFoundError("Sales form not found.")
        return document

    def kind_of(self, doc_type: SalesDocType) -> SalesDocumentKind:
        return self.kinds[doc_type]

    # ---------- creating ----------

    def create(self, company_id: int, data: SalesDocumentCreate) -> SalesDocument:
        kind = self.kind_of(data.doc_type)

        customer = self.customer_repository.get(company_id, data.customer_id)
        if customer is None or not customer.is_active:
            raise BusinessRuleError("Please choose an active customer.")
        if data.expiration_date is not None and data.expiration_date < data.doc_date:
            raise BusinessRuleError("The expiration date cannot be before the date.")

        line_values = self.line_builder.build(company_id, data.lines)
        totals = calculate_totals(line_values, data.discount_type, data.discount_value, data.shipping_amount)
        totals.add_tax(self.tax_calculator.calculate(company_id, customer, data.tax_code_id, line_values, totals))
        if totals.total <= 0:
            raise BusinessRuleError("The total must be more than zero.")

        money_account = kind.choose_money_account(company_id, data.money_account_id, self.account_repository, self.system_accounts)

        document = SalesDocument(
            company_id=company_id,
            doc_type=kind.doc_type,
            doc_number=self.numbering.next_number(company_id, kind.doc_type.value),
            customer_id=customer.id,
            doc_date=data.doc_date,
            expiration_date=data.expiration_date,
            status=kind.initial_status,
            memo=data.memo,
            subtotal=totals.subtotal,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            discount_amount=totals.discount_amount,
            shipping_amount=totals.shipping_amount,
            tax_code_id=totals.tax.tax_code_id,
            tax_amount=totals.tax_amount,
            total=totals.total,
            money_account_id=money_account.id if money_account else None,
            payment_method=data.payment_method,
            reference_no=data.reference_no,
        )
        for values in line_values:
            document.lines.append(SalesDocumentLine(**values.as_dict()))
        self.repository.add(document)

        if kind.journal_source is not None:
            ledger_lines = income_ledger_lines(company_id, document.lines, totals, self.system_accounts, kind.is_return)
            ledger_lines.extend(kind.other_side(company_id, document, self.system_accounts))
            label = f"{kind.label} {document.doc_number} - {customer.display_name}"
            stock = StockSource(TAX_SOURCE, document.id, document.doc_date, label)
            ledger_lines.extend(self.inventory.cost_of_sales_lines(company_id, document.lines, stock, kind.is_return))
            entry = self.ledger.post(
                company_id=company_id,
                entry_date=document.doc_date,
                source_type=kind.journal_source,
                source_id=document.id,
                memo=label,
                lines=ledger_lines,
            )
            document.journal_entry_id = entry.id
            # Only forms that post are real sales (estimates and delayed forms are not yet).
            self.tax_calculator.record(company_id, TAX_SOURCE, document.id, document.doc_date, totals.tax, kind.is_return)

        self.commit()
        return document

    # ---------- changing ----------

    def set_estimate_status(self, company_id: int, document_id: int, status: SalesDocStatus) -> SalesDocument:
        document = self.get(company_id, document_id)
        if document.doc_type != SalesDocType.ESTIMATE:
            raise BusinessRuleError("Only estimates can be accepted or rejected.")
        if status not in ESTIMATE_STATUSES_USERS_CAN_SET:
            raise BusinessRuleError("An estimate can be set to pending, accepted or rejected.")
        if document.status in (SalesDocStatus.CLOSED, SalesDocStatus.VOID):
            raise BusinessRuleError(f"This estimate is {document.status.value.lower()}.")
        if status == SalesDocStatus.REJECTED and document.amount_applied > 0:
            raise BusinessRuleError("This estimate has already been partly invoiced.")
        document.status = status
        self.commit()
        return document

    def void(self, company_id: int, document_id: int) -> SalesDocument:
        document = self.get(company_id, document_id)
        if document.status == SalesDocStatus.VOID:
            raise BusinessRuleError("This form is already void.")
        if document.doc_type in (SalesDocType.CREDIT_MEMO, SalesDocType.ESTIMATE) and document.amount_applied > 0:
            raise BusinessRuleError("This form has already been used. It cannot be voided.")
        if document.deposit_id is not None:
            raise BusinessRuleError("This sales receipt is part of a bank deposit. Remove it from the deposit first.")
        if document.invoice_id is not None:
            raise BusinessRuleError("This delayed charge or credit is on an invoice. Void that invoice first.")

        kind = self.kind_of(document.doc_type)
        if document.journal_entry_id is not None:
            original = self.journal_repository.get(company_id, document.journal_entry_id)
            memo = f"Void of {kind.label.lower()} {document.doc_number}"
            self.ledger.reverse(company_id, original, date.today(), JournalSource.SALES_DOC_VOID, memo)
            self.tax_calculator.void(company_id, TAX_SOURCE, document.id)
            self.inventory.undo(company_id, TAX_SOURCE, document.id, date.today(), memo)

        document.status = SalesDocStatus.VOID
        self.commit()
        return document
