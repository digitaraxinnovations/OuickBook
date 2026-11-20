"""
Bills, vendor credits and purchase orders. The differences between them
live in purchase_kinds.py; this class does what they have in common.
"""

from datetime import date, timedelta

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import PurchaseDocument, PurchaseDocumentLine
from app.models.enums import JournalSource, PurchaseDocStatus, PurchaseDocType
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.repositories.sales_repositories import PaymentTermRepository
from app.schemas.purchase import PurchaseDocumentCreate, PurchaseLineInput
from app.services.base import BaseService
from app.services.ledger_service import LedgerService
from app.services.numbering import DocumentNumberService
from app.services.purchase_kinds import PurchaseKind
from app.services.system_accounts import SystemAccounts


class PurchaseDocumentService(BaseService):
    def __init__(
        self,
        session,
        repository: PurchaseDocumentRepository,
        vendor_repository: VendorRepository,
        customer_repository: CustomerRepository,
        account_repository: AccountRepository,
        company_repository: CompanyRepository,
        terms_repository: PaymentTermRepository,
        journal_repository: JournalRepository,
        system_accounts: SystemAccounts,
        numbering: DocumentNumberService,
        ledger: LedgerService,
        kinds: list[PurchaseKind],
    ):
        super().__init__(session)
        self.repository = repository
        self.vendor_repository = vendor_repository
        self.customer_repository = customer_repository
        self.account_repository = account_repository
        self.company_repository = company_repository
        self.terms_repository = terms_repository
        self.journal_repository = journal_repository
        self.system_accounts = system_accounts
        self.numbering = numbering
        self.ledger = ledger
        self.kinds = {}
        for kind in kinds:
            self.kinds[kind.doc_type] = kind

    # ---------- reading ----------

    def list(self, company_id: int, doc_type=None, vendor_id=None, status=None) -> list[PurchaseDocument]:
        return self.repository.list_filtered(company_id, doc_type, vendor_id, status)

    def get(self, company_id: int, document_id: int) -> PurchaseDocument:
        document = self.repository.get(company_id, document_id)
        if document is None:
            raise NotFoundError("Vendor form not found.")
        return document

    # ---------- creating ----------

    def create(self, company_id: int, data: PurchaseDocumentCreate, purchase_order: PurchaseDocument | None = None) -> PurchaseDocument:
        kind = self.kinds[data.doc_type]

        vendor = self.vendor_repository.get(company_id, data.vendor_id)
        if vendor is None or not vendor.is_active:
            raise BusinessRuleError("Please choose an active vendor.")

        document = PurchaseDocument(
            company_id=company_id,
            doc_type=kind.doc_type,
            vendor_id=vendor.id,
            doc_date=data.doc_date,
            status=PurchaseDocStatus.OPEN,
            memo=data.memo,
            amount_applied=ZERO,
            purchase_order_id=purchase_order.id if purchase_order else None,
        )
        if kind.auto_number:
            document.doc_number = self.numbering.next_number(company_id, kind.doc_type.value)
        else:
            document.doc_number = data.doc_number

        if kind.has_due_date:
            document.due_date, document.terms_id = self.due_date_for(company_id, vendor, data)

        total = ZERO
        for line_data in data.lines:
            line = self.build_line(company_id, line_data)
            document.lines.append(line)
            total += line.amount
        if total <= 0:
            raise BusinessRuleError("The total must be more than zero.")
        document.total = total

        self.repository.add(document)

        if kind.journal_source is not None:
            entry = self.ledger.post(
                company_id=company_id,
                entry_date=document.doc_date,
                source_type=kind.journal_source,
                source_id=document.id,
                memo=f"{kind.label} {document.doc_number or ''} - {vendor.display_name}".replace("  ", " "),
                lines=kind.ledger_lines(company_id, document, self.system_accounts),
            )
            document.journal_entry_id = entry.id

        self.commit()
        return document

    def build_line(self, company_id: int, data: PurchaseLineInput) -> PurchaseDocumentLine:
        account = self.account_repository.get(company_id, data.account_id)
        if account is None or not account.is_active:
            raise BusinessRuleError("Please choose an active category for every line.")
        if data.customer_id is not None and self.customer_repository.get(company_id, data.customer_id) is None:
            raise BusinessRuleError("The billable customer does not exist.")
        return PurchaseDocumentLine(
            account_id=account.id,
            description=data.description,
            quantity=data.quantity,
            rate=data.rate,
            amount=to_money(data.quantity * data.rate),
            customer_id=data.customer_id,
        )

    def due_date_for(self, company_id: int, vendor, data: PurchaseDocumentCreate):
        """Bill due date: typed date, else bill terms, else vendor terms, else the company default."""
        terms_id = data.terms_id or vendor.terms_id
        if data.due_date is not None:
            due_date = data.due_date
        elif terms_id is not None:
            term = self.terms_repository.get(company_id, terms_id)
            if term is None:
                raise BusinessRuleError("Those payment terms do not exist.")
            due_date = data.doc_date + timedelta(days=term.due_days)
        else:
            company = self.company_repository.get(company_id)
            due_date = data.doc_date + timedelta(days=company.payment_terms_days)
        if due_date < data.doc_date:
            raise BusinessRuleError("The due date cannot be before the bill date.")
        return due_date, terms_id

    # ---------- purchase orders ----------

    def convert_purchase_order(self, company_id: int, order_id: int, bill_date: date, bill_number: str | None) -> PurchaseDocument:
        """Create a bill with the purchase order's lines and close the order."""
        order = self.get(company_id, order_id)
        if order.doc_type != PurchaseDocType.PURCHASE_ORDER:
            raise BusinessRuleError("Only purchase orders can be turned into bills.")
        if order.status != PurchaseDocStatus.OPEN:
            raise BusinessRuleError(f"This purchase order is {order.status.value.lower()}.")

        lines = []
        for line in order.lines:
            lines.append(
                PurchaseLineInput(
                    account_id=line.account_id,
                    description=line.description,
                    quantity=line.quantity,
                    rate=line.rate,
                    customer_id=line.customer_id,
                )
            )
        data = PurchaseDocumentCreate(
            doc_type=PurchaseDocType.BILL,
            vendor_id=order.vendor_id,
            doc_date=bill_date,
            doc_number=bill_number,
            memo=order.memo,
            lines=lines,
        )
        order.amount_applied = order.total
        order.status = PurchaseDocStatus.CLOSED
        return self.create(company_id, data, purchase_order=order)

    def close_purchase_order(self, company_id: int, order_id: int) -> PurchaseDocument:
        order = self.get(company_id, order_id)
        if order.doc_type != PurchaseDocType.PURCHASE_ORDER or order.status != PurchaseDocStatus.OPEN:
            raise BusinessRuleError("Only open purchase orders can be closed.")
        order.status = PurchaseDocStatus.CLOSED
        self.commit()
        return order

    # ---------- voiding ----------

    def void(self, company_id: int, document_id: int) -> PurchaseDocument:
        document = self.get(company_id, document_id)
        if document.status == PurchaseDocStatus.VOID:
            raise BusinessRuleError("This form is already void.")
        if document.amount_applied > 0 and document.doc_type != PurchaseDocType.PURCHASE_ORDER:
            raise BusinessRuleError("This form has payments or has been used. It cannot be voided.")

        if document.journal_entry_id is not None:
            original = self.journal_repository.get(company_id, document.journal_entry_id)
            label = self.kinds[document.doc_type].label.lower()
            self.ledger.reverse(company_id, original, date.today(), JournalSource.PURCHASE_VOID, f"Void of {label}")

        # A voided bill that came from a purchase order re-opens the order.
        if document.purchase_order_id is not None:
            order = self.repository.get(company_id, document.purchase_order_id)
            order.status = PurchaseDocStatus.OPEN
            order.amount_applied = ZERO

        document.status = PurchaseDocStatus.VOID
        self.commit()
        return document
