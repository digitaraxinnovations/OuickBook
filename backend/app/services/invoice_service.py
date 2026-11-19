"""
Invoices.

Creating an invoice records the sale in the ledger:
    Debit  Accounts Receivable          (the customer now owes you)
    Credit Income account(s)            (you earned the money)
    Debit  Discounts Given / Credit Shipping Income   (when used)
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import Invoice, InvoiceLine, SalesDocument
from app.models.enums import DiscountType, InvoiceStatus, JournalSource, SalesDocStatus, SalesDocType
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.sales_repositories import SalesDocumentRepository
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate
from app.schemas.payment import PaymentApplicationInput, PaymentCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.payment_service import PaymentService
from app.services.sales_common import SalesLineBuilder, SalesLineValues, calculate_totals, income_ledger_lines
from app.services.system_accounts import SystemAccounts
from app.services.terms_service import TermsService

# Rounding can leave a few cents when an estimate is invoiced in parts.
ROUNDING_TOLERANCE = Decimal("0.05")


class InvoiceService(BaseService):
    def __init__(
        self,
        session,
        invoice_repository: InvoiceRepository,
        customer_repository: CustomerRepository,
        company_repository: CompanyRepository,
        journal_repository: JournalRepository,
        sales_document_repository: SalesDocumentRepository,
        line_builder: SalesLineBuilder,
        system_accounts: SystemAccounts,
        terms_service: TermsService,
        ledger: LedgerService,
        payment_service: PaymentService,
    ):
        super().__init__(session)
        self.invoice_repository = invoice_repository
        self.customer_repository = customer_repository
        self.company_repository = company_repository
        self.journal_repository = journal_repository
        self.sales_document_repository = sales_document_repository
        self.line_builder = line_builder
        self.system_accounts = system_accounts
        self.terms_service = terms_service
        self.ledger = ledger
        self.payment_service = payment_service

    # ---------- reading ----------

    def list(self, company_id: int, customer_id: int | None = None, status: InvoiceStatus | None = None) -> list[Invoice]:
        return self.invoice_repository.list_filtered(company_id, customer_id, status)

    def get(self, company_id: int, invoice_id: int) -> Invoice:
        invoice = self.invoice_repository.get(company_id, invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    # ---------- creating ----------

    def create(self, company_id: int, data: InvoiceCreate, estimate: SalesDocument | None = None) -> Invoice:
        customer = self.customer_repository.get(company_id, data.customer_id)
        if customer is None or not customer.is_active:
            raise BusinessRuleError("Please choose an active customer.")

        company = self.company_repository.get(company_id)
        if data.due_date is not None:
            due_date = data.due_date
            terms_id = data.terms_id
        else:
            due_date, terms_id = self.terms_service.due_date_for(company, customer, data.invoice_date, data.terms_id)
        if due_date < data.invoice_date:
            raise BusinessRuleError("The due date cannot be before the invoice date.")

        line_values = self.line_builder.build(company_id, data.lines)
        delayed_documents = self.collect_delayed_documents(company_id, customer.id, data.delayed_document_ids)
        for document in delayed_documents:
            line_values.extend(self.lines_from_delayed_document(document))
        if len(line_values) == 0:
            raise BusinessRuleError("Add at least one line to the invoice.")

        totals = calculate_totals(line_values, data.discount_type, data.discount_value, data.shipping_amount)
        if totals.total <= 0:
            raise BusinessRuleError("The invoice total must be more than zero.")
        if data.deposit_amount > totals.total:
            raise BusinessRuleError("The deposit cannot be more than the invoice total.")

        invoice = Invoice(
            company_id=company_id,
            invoice_number=str(company.next_invoice_number),
            customer_id=customer.id,
            invoice_date=data.invoice_date,
            due_date=due_date,
            terms_id=terms_id,
            status=InvoiceStatus.OPEN,
            memo=data.memo,
            subtotal=totals.subtotal,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            discount_amount=totals.discount_amount,
            shipping_amount=totals.shipping_amount,
            total=totals.total,
            amount_paid=ZERO,
            estimate_id=estimate.id if estimate else None,
        )
        for values in line_values:
            invoice.lines.append(InvoiceLine(**values.as_dict()))
        company.next_invoice_number += 1
        self.invoice_repository.add(invoice)

        receivable = self.system_accounts.get(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)
        ledger_lines = [LedgerLine(receivable.id, debit=totals.total)]
        ledger_lines.extend(income_ledger_lines(company_id, invoice.lines, totals, self.system_accounts, is_return=False))
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=invoice.invoice_date,
            source_type=JournalSource.INVOICE,
            source_id=invoice.id,
            memo=f"Invoice {invoice.invoice_number} - {customer.display_name}",
            lines=ledger_lines,
        )
        invoice.journal_entry_id = entry.id

        for document in delayed_documents:
            document.status = SalesDocStatus.CLOSED
            document.invoice_id = invoice.id

        if data.deposit_amount > 0:
            self.payment_service.receive(
                company_id,
                PaymentCreate(
                    customer_id=customer.id,
                    payment_date=data.invoice_date,
                    amount=data.deposit_amount,
                    deposit_account_id=data.deposit_account_id,
                    memo=f"Deposit on invoice {invoice.invoice_number}",
                    applications=[PaymentApplicationInput(invoice_id=invoice.id, amount=data.deposit_amount)],
                ),
                commit=False,
            )

        self.commit()
        return invoice

    def collect_delayed_documents(self, company_id: int, customer_id: int, document_ids: list[int]) -> list[SalesDocument]:
        documents = []
        for document_id in document_ids:
            document = self.sales_document_repository.get(company_id, document_id)
            is_delayed = document is not None and document.doc_type in (SalesDocType.DELAYED_CHARGE, SalesDocType.DELAYED_CREDIT)
            if not is_delayed or document.customer_id != customer_id:
                raise BusinessRuleError("Only this customer's delayed charges and credits can be added.")
            if document.status != SalesDocStatus.OPEN:
                raise BusinessRuleError(f"Delayed {document.doc_type.value.lower()} {document.doc_number} was already used.")
            documents.append(document)
        return documents

    def lines_from_delayed_document(self, document: SalesDocument) -> list[SalesLineValues]:
        """Copy the lines. A delayed credit lowers the invoice, so its amounts become negative."""
        sign = Decimal("1")
        if document.doc_type == SalesDocType.DELAYED_CREDIT:
            sign = Decimal("-1")
        label = "Delayed charge" if sign > 0 else "Delayed credit"

        result = []
        for line in document.lines:
            description = (line.description or "") + f" ({label} {document.doc_number})"
            result.append(
                SalesLineValues(
                    product_id=line.product_id,
                    income_account_id=line.income_account_id,
                    description=description.strip(),
                    quantity=line.quantity,
                    rate=line.rate * sign,
                    amount=line.amount * sign,
                )
            )
        return result

    # ---------- estimates -> invoices (progress invoicing) ----------

    def create_from_estimate(self, company_id: int, estimate_id: int, invoice_date: date, percent: Decimal) -> Invoice:
        estimate = self.sales_document_repository.get(company_id, estimate_id)
        if estimate is None or estimate.doc_type != SalesDocType.ESTIMATE:
            raise NotFoundError("Estimate not found.")
        if estimate.status in (SalesDocStatus.REJECTED, SalesDocStatus.CLOSED, SalesDocStatus.VOID):
            raise BusinessRuleError(f"This estimate is {estimate.status.value.lower()} and cannot be invoiced.")

        factor = percent / Decimal("100")
        lines = []
        for line in estimate.lines:
            lines.append(
                InvoiceLineCreate(
                    product_id=line.product_id,
                    description=line.description,
                    quantity=line.quantity,
                    rate=to_money(line.rate * factor),
                )
            )

        discount_value = estimate.discount_value
        if estimate.discount_type == DiscountType.AMOUNT:
            discount_value = to_money(estimate.discount_value * factor)

        data = InvoiceCreate(
            customer_id=estimate.customer_id,
            invoice_date=invoice_date,
            memo=estimate.memo,
            lines=lines,
            discount_type=estimate.discount_type,
            discount_value=discount_value,
            shipping_amount=to_money(estimate.shipping_amount * factor),
        )

        # Check before saving that we do not invoice more than the estimate.
        preview = calculate_totals(
            self.line_builder.build(company_id, lines), data.discount_type, data.discount_value, data.shipping_amount
        )
        if estimate.amount_applied + preview.total > estimate.total + ROUNDING_TOLERANCE:
            raise BusinessRuleError(
                f"Only {estimate.remaining} of this estimate is left to invoice; this invoice would be {preview.total}."
            )

        estimate.amount_applied = estimate.amount_applied + preview.total
        if estimate.remaining <= ROUNDING_TOLERANCE:
            estimate.status = SalesDocStatus.CLOSED
        else:
            estimate.status = SalesDocStatus.ACCEPTED
        return self.create(company_id, data, estimate=estimate)

    # ---------- voiding ----------

    def void(self, company_id: int, invoice_id: int) -> Invoice:
        invoice = self.get(company_id, invoice_id)
        if invoice.status == InvoiceStatus.VOID:
            raise BusinessRuleError("This invoice is already void.")
        if invoice.amount_paid > 0:
            raise BusinessRuleError("This invoice has payments. It cannot be voided.")

        original_entry = self.journal_repository.get(company_id, invoice.journal_entry_id)
        self.ledger.reverse(
            company_id=company_id,
            original=original_entry,
            entry_date=date.today(),
            source_type=JournalSource.INVOICE_VOID,
            memo=f"Void of invoice {invoice.invoice_number}",
        )
        # Late fees were posted as separate entries - reverse those too.
        for entry in self.journal_repository.list_for_source(company_id, JournalSource.LATE_FEE, invoice.id):
            self.ledger.reverse(company_id, entry, date.today(), JournalSource.INVOICE_VOID, "Void of late fee")

        # Give back delayed charges/credits and the estimate amount.
        for document in self.sales_document_repository.list_filtered(company_id, customer_id=invoice.customer_id):
            if document.invoice_id == invoice.id:
                document.invoice_id = None
                document.status = SalesDocStatus.OPEN
        if invoice.estimate_id is not None:
            estimate = self.sales_document_repository.get(company_id, invoice.estimate_id)
            estimate.amount_applied = max(ZERO, estimate.amount_applied - invoice.total)
            estimate.status = SalesDocStatus.ACCEPTED

        invoice.status = InvoiceStatus.VOID
        self.commit()
        return invoice
