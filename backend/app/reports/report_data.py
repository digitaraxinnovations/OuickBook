"""
Data shared by many reports.

- SourceNames:  for each journal entry, the transaction type ("Invoice"),
                its number and the customer or vendor - looked up from the
                transaction that created it, so a check numbered later
                still shows its number.
- LedgerFacts:  income and expense amounts with their date, customer,
                vendor, class, location and project - on the accrual or the
                cash basis. Profit and Loss style reports group these facts.

Cash basis: invoices and bills count when they are paid. Each payment
counts its share of the invoice's (or bill's) income and expense lines on the
payment date. Everything else (sales receipts, expenses, credit memos,
journal entries...) counts on its own date, the same as accrual.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import (
    Account,
    BillPayment,
    Customer,
    Expense,
    Invoice,
    JournalEntry,
    JournalLine,
    Payment,
    PurchaseDocument,
    SalesDocument,
    Location,
    TrackingClass,
    Vendor,
)
from app.models.enums import AccountType, JournalSource, PurchaseDocType

# Transaction type shown in detail reports.
SOURCE_LABELS = {
    JournalSource.MANUAL: "Journal Entry",
    JournalSource.INVOICE: "Invoice",
    JournalSource.INVOICE_VOID: "Invoice (void)",
    JournalSource.PAYMENT: "Payment",
    JournalSource.EXPENSE: "Expense",
    JournalSource.SALES_RECEIPT: "Sales Receipt",
    JournalSource.CREDIT_MEMO: "Credit Memo",
    JournalSource.REFUND_RECEIPT: "Refund",
    JournalSource.SALES_DOC_VOID: "Sales form (void)",
    JournalSource.DEPOSIT: "Deposit",
    JournalSource.LATE_FEE: "Late Fee",
    JournalSource.CHECK: "Check",
    JournalSource.EXPENSE_VOID: "Expense (void)",
    JournalSource.BILL: "Bill",
    JournalSource.VENDOR_CREDIT: "Vendor Credit",
    JournalSource.BILL_PAYMENT: "Bill Payment",
    JournalSource.PURCHASE_VOID: "Vendor form (void)",
    JournalSource.TRANSFER: "Transfer",
    JournalSource.SALES_TAX_PAYMENT: "Sales Tax Payment",
    JournalSource.SALES_TAX_ADJUST: "Sales Tax Adjustment",
    JournalSource.CARD_CREDIT: "Credit Card Credit",
    JournalSource.BANK_DEPOSIT: "Bank Deposit",
    JournalSource.INVENTORY_ADJUST: "Inventory Adjustment",
    JournalSource.INVENTORY_START: "Inventory Starting Value",
    JournalSource.PAYROLL: "Payroll",
    JournalSource.PAYROLL_VOID: "Payroll (void)",
    JournalSource.PAYROLL_LIABILITY: "Payroll Liability Payment",
}

INVOICE_SOURCES = (JournalSource.INVOICE, JournalSource.INVOICE_VOID, JournalSource.LATE_FEE)
SALES_DOC_SOURCES = (JournalSource.SALES_RECEIPT, JournalSource.CREDIT_MEMO, JournalSource.REFUND_RECEIPT, JournalSource.SALES_DOC_VOID)
EXPENSE_SOURCES = (JournalSource.EXPENSE, JournalSource.CHECK, JournalSource.CARD_CREDIT, JournalSource.EXPENSE_VOID)
PURCHASE_SOURCES = (JournalSource.BILL, JournalSource.VENDOR_CREDIT, JournalSource.PURCHASE_VOID)


class EntryName:
    """Who and what a journal entry is about."""

    def __init__(self, type_label: str, number: str = "", name: str = "", customer_id: int | None = None, vendor_id: int | None = None):
        self.type_label = type_label
        self.number = number
        self.name = name
        self.customer_id = customer_id
        self.vendor_id = vendor_id


class SourceNames:
    def __init__(self, session):
        self.session = session

    def for_entries(self, company_id: int, entries: list[JournalEntry]) -> dict[int, EntryName]:
        """{entry id: EntryName} for many entries at once (a few queries, not one per entry)."""
        ids_per_group = {"invoice": set(), "sales": set(), "payment": set(), "expense": set(), "purchase": set(), "bill_payment": set()}
        for entry in entries:
            if entry.source_id is None:
                continue
            group = self.group_of(entry.source_type)
            if group is not None:
                ids_per_group[group].add(entry.source_id)

        customers = self.names(Customer, company_id)
        vendors = self.names(Vendor, company_id)
        documents = {}
        for record in self.load(Invoice, ids_per_group["invoice"]):
            documents[("invoice", record.id)] = (record.invoice_number, record.customer_id, None)
        for record in self.load(SalesDocument, ids_per_group["sales"]):
            documents[("sales", record.id)] = (record.doc_number, record.customer_id, None)
        for record in self.load(Payment, ids_per_group["payment"]):
            documents[("payment", record.id)] = (record.reference_no or "", record.customer_id, None)
        for record in self.load(Expense, ids_per_group["expense"]):
            documents[("expense", record.id)] = (record.check_number or record.reference_no or "", None, record.vendor_id)
        for record in self.load(PurchaseDocument, ids_per_group["purchase"]):
            documents[("purchase", record.id)] = (record.doc_number or "", None, record.vendor_id)
        for record in self.load(BillPayment, ids_per_group["bill_payment"]):
            documents[("bill_payment", record.id)] = (record.check_number or "", None, record.vendor_id)

        result = {}
        for entry in entries:
            label = SOURCE_LABELS.get(entry.source_type, entry.source_type.value.replace("_", " ").title())
            group = self.group_of(entry.source_type)
            found = documents.get((group, entry.source_id)) if group else None
            if found is None:
                result[entry.id] = EntryName(label)
                continue
            number, customer_id, vendor_id = found
            name = customers.get(customer_id, "") if customer_id else vendors.get(vendor_id, "")
            result[entry.id] = EntryName(label, number or "", name, customer_id, vendor_id)
        return result

    def group_of(self, source_type: JournalSource) -> str | None:
        if source_type in INVOICE_SOURCES:
            return "invoice"
        if source_type in SALES_DOC_SOURCES:
            return "sales"
        if source_type == JournalSource.PAYMENT:
            return "payment"
        if source_type in EXPENSE_SOURCES:
            return "expense"
        if source_type in PURCHASE_SOURCES:
            return "purchase"
        if source_type == JournalSource.BILL_PAYMENT:
            return "bill_payment"
        return None

    def load(self, model, ids: set[int]) -> list:
        if not ids:
            return []
        return list(self.session.scalars(select(model).where(model.id.in_(ids))))

    def names(self, model, company_id: int) -> dict[int, str]:
        query = select(model.id, model.display_name).where(model.company_id == company_id)
        result = {}
        for record_id, name in self.session.execute(query):
            result[record_id] = name
        return result


class Fact:
    """One income or expense amount. `amount` is credit - debit (income +, expense -)."""

    def __init__(self, account: Account, when: date, amount: Decimal, line: JournalLine, name: EntryName):
        self.account = account
        self.when = when
        self.amount = amount
        self.customer_id = name.customer_id
        self.vendor_id = name.vendor_id
        self.class_id = line.class_id
        self.location_id = line.location_id
        self.project_id = line.project_id


class LedgerFacts:
    def __init__(self, session, names: SourceNames):
        self.session = session
        self.names = names

    def profit_and_loss(self, company_id: int, start: date | None, end: date, basis: str) -> list[Fact]:
        facts = []
        lines = self.income_expense_lines(company_id, start, end)
        entries = {}
        for line in lines:
            entries[line.entry.id] = line.entry
        entry_names = self.names.for_entries(company_id, list(entries.values()))

        for line in lines:
            entry = line.entry
            if basis == "cash" and self.counts_when_paid(entry):
                continue
            facts.append(Fact(line.account, entry.entry_date, line.credit - line.debit, line, entry_names[entry.id]))

        if basis == "cash":
            facts.extend(self.paid_invoice_facts(company_id, start, end))
            facts.extend(self.paid_bill_facts(company_id, start, end))
        return facts

    def income_expense_lines(self, company_id: int, start: date | None, end: date, entry_ids: list[int] | None = None) -> list[JournalLine]:
        query = (
            select(JournalLine)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(JournalEntry.company_id == company_id, Account.account_type.in_((AccountType.INCOME, AccountType.EXPENSE)))
        )
        if entry_ids is not None:
            query = query.where(JournalEntry.id.in_(entry_ids))
        else:
            query = query.where(JournalEntry.entry_date <= end)
            if start is not None:
                query = query.where(JournalEntry.entry_date >= start)
        return list(self.session.scalars(query.order_by(JournalEntry.entry_date, JournalLine.id)))

    def counts_when_paid(self, entry: JournalEntry) -> bool:
        """Invoices, their late fees and bills (and their voids) wait for payment on the cash basis."""
        if entry.source_type in INVOICE_SOURCES or entry.source_type == JournalSource.BILL:
            return True
        if entry.source_type == JournalSource.PURCHASE_VOID:
            document = self.session.get(PurchaseDocument, entry.source_id)
            return document is not None and document.doc_type == PurchaseDocType.BILL
        return False

    def paid_invoice_facts(self, company_id: int, start: date | None, end: date) -> list[Fact]:
        query = select(Payment).where(Payment.company_id == company_id, Payment.payment_date <= end)
        if start is not None:
            query = query.where(Payment.payment_date >= start)
        facts = []
        for payment in self.session.scalars(query):
            for application in payment.applications:
                invoice = application.invoice
                if invoice.total == 0:
                    continue
                share = application.amount / invoice.total
                entry_ids = [invoice.journal_entry_id] + self.late_fee_entry_ids(company_id, invoice.id)
                facts.extend(self.shared_facts(company_id, entry_ids, share, payment.payment_date))
        return facts

    def paid_bill_facts(self, company_id: int, start: date | None, end: date) -> list[Fact]:
        query = select(BillPayment).where(BillPayment.company_id == company_id, BillPayment.payment_date <= end)
        if start is not None:
            query = query.where(BillPayment.payment_date >= start)
        facts = []
        for payment in self.session.scalars(query):
            for application in payment.applications:
                bill = application.bill
                if bill.total == 0 or bill.journal_entry_id is None:
                    continue
                share = application.amount / bill.total
                facts.extend(self.shared_facts(company_id, [bill.journal_entry_id], share, payment.payment_date))
        return facts

    def late_fee_entry_ids(self, company_id: int, invoice_id: int) -> list[int]:
        query = select(JournalEntry.id).where(
            JournalEntry.company_id == company_id,
            JournalEntry.source_type == JournalSource.LATE_FEE,
            JournalEntry.source_id == invoice_id,
        )
        return list(self.session.scalars(query))

    def shared_facts(self, company_id: int, entry_ids: list[int], share: Decimal, when: date) -> list[Fact]:
        """`share` of each income / expense line of these entries, dated `when`."""
        lines = self.income_expense_lines(company_id, None, when, entry_ids=entry_ids)
        entries = {}
        for line in lines:
            entries[line.entry.id] = line.entry
        entry_names = self.names.for_entries(company_id, list(entries.values()))
        facts = []
        for line in lines:
            amount = ((line.credit - line.debit) * share).quantize(Decimal("0.01"))
            facts.append(Fact(line.account, when, amount, line, entry_names[line.entry.id]))
        return facts


def filter_facts(facts: list[Fact], options) -> list[Fact]:
    """Keep the facts that match the report's filters (class, location, customer...)."""
    result = []
    for fact in facts:
        if options.class_id is not None and fact.class_id != options.class_id:
            continue
        if options.location_id is not None and fact.location_id != options.location_id:
            continue
        if options.customer_id is not None and fact.customer_id != options.customer_id:
            continue
        if options.vendor_id is not None and fact.vendor_id != options.vendor_id:
            continue
        if options.project_id is not None and fact.project_id != options.project_id:
            continue
        result.append(fact)
    return result


class ListNames:
    """{id: name} of customers, vendors, classes or locations."""

    MODELS = {"customer": (Customer, "display_name"), "vendor": (Vendor, "display_name"), "class": (TrackingClass, "name"), "location": (Location, "name")}

    def __init__(self, session):
        self.session = session

    def for_kind(self, company_id: int, kind: str) -> dict[int, str]:
        model, column_name = self.MODELS[kind]
        column = getattr(model, column_name)
        result = {}
        for record_id, name in self.session.execute(select(model.id, column).where(model.company_id == company_id)):
            result[record_id] = name
        return result
