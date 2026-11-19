"""
Invoices.

Creating an invoice records the sale in the ledger:
    Debit  Accounts Receivable   (the customer now owes you)
    Credit Income account(s)     (you earned the money)
"""

from datetime import date, timedelta

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import Account, Invoice, InvoiceLine
from app.models.enums import InvoiceStatus, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService


class InvoiceService(BaseService):
    def __init__(
        self,
        session,
        invoice_repository: InvoiceRepository,
        customer_repository: CustomerRepository,
        product_repository: ProductRepository,
        account_repository: AccountRepository,
        company_repository: CompanyRepository,
        journal_repository: JournalRepository,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.invoice_repository = invoice_repository
        self.customer_repository = customer_repository
        self.product_repository = product_repository
        self.account_repository = account_repository
        self.company_repository = company_repository
        self.journal_repository = journal_repository
        self.ledger = ledger

    # ---------- reading ----------

    def list(self, company_id: int, customer_id: int | None = None, status: InvoiceStatus | None = None) -> list[Invoice]:
        return self.invoice_repository.list_filtered(company_id, customer_id, status)

    def get(self, company_id: int, invoice_id: int) -> Invoice:
        invoice = self.invoice_repository.get(company_id, invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    # ---------- creating ----------

    def create(self, company_id: int, data: InvoiceCreate) -> Invoice:
        customer = self.customer_repository.get(company_id, data.customer_id)
        if customer is None or not customer.is_active:
            raise BusinessRuleError("Please choose an active customer.")

        company = self.company_repository.get(company_id)
        due_date = data.due_date
        if due_date is None:
            due_date = data.invoice_date + timedelta(days=company.payment_terms_days)
        if due_date < data.invoice_date:
            raise BusinessRuleError("The due date cannot be before the invoice date.")

        sales_account = self.account_repository.get_by_system_key(company_id, SystemAccount.SALES)

        invoice = Invoice(
            company_id=company_id,
            invoice_number=str(company.next_invoice_number),
            customer_id=customer.id,
            invoice_date=data.invoice_date,
            due_date=due_date,
            status=InvoiceStatus.OPEN,
            memo=data.memo,
            amount_paid=ZERO,
        )
        total = ZERO
        for line_data in data.lines:
            line = self.build_line(company_id, line_data, sales_account)
            invoice.lines.append(line)
            total += line.amount

        if total <= 0:
            raise BusinessRuleError("The invoice total must be more than zero.")
        invoice.total = total

        company.next_invoice_number += 1
        self.invoice_repository.add(invoice)

        entry = self.ledger.post(
            company_id=company_id,
            entry_date=invoice.invoice_date,
            source_type=JournalSource.INVOICE,
            source_id=invoice.id,
            memo=f"Invoice {invoice.invoice_number} - {customer.display_name}",
            lines=self.build_ledger_lines(company_id, invoice),
        )
        invoice.journal_entry_id = entry.id

        self.commit()
        return invoice

    def build_line(self, company_id: int, data: InvoiceLineCreate, sales_account: Account) -> InvoiceLine:
        description = data.description
        income_account_id = sales_account.id

        if data.product_id is not None:
            product = self.product_repository.get(company_id, data.product_id)
            if product is None:
                raise BusinessRuleError(f"Product {data.product_id} does not exist.")
            income_account_id = product.income_account_id
            if description is None:
                description = product.description or product.name

        return InvoiceLine(
            product_id=data.product_id,
            income_account_id=income_account_id,
            description=description,
            quantity=data.quantity,
            rate=data.rate,
            amount=to_money(data.quantity * data.rate),
        )

    def build_ledger_lines(self, company_id: int, invoice: Invoice) -> list[LedgerLine]:
        receivable = self.account_repository.get_by_system_key(company_id, SystemAccount.ACCOUNTS_RECEIVABLE)
        lines = [LedgerLine(receivable.id, debit=invoice.total)]

        # Add up the invoice lines per income account.
        amount_per_account = {}
        for line in invoice.lines:
            current = amount_per_account.get(line.income_account_id, ZERO)
            amount_per_account[line.income_account_id] = current + line.amount

        for account_id, amount in amount_per_account.items():
            if amount > 0:
                lines.append(LedgerLine(account_id, credit=amount))
            elif amount < 0:
                # A discount line (negative amount) reduces income, so it is a debit.
                lines.append(LedgerLine(account_id, debit=-amount))
        return lines

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
        invoice.status = InvoiceStatus.VOID
        self.commit()
        return invoice
