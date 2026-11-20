"""
Who owes you and what you owe.

A/R: Aging Summary (per customer, by age), Aging Detail, Open Invoices,
     Collections, Customer Balance Summary and Detail.
A/P: Aging Summary (per vendor, by age), Aging Detail, Unpaid Bills,
     Vendor Balance Summary and Detail.

Aging uses the report date: days past due = report date - due date.
"""

from datetime import date
from decimal import Decimal

from app.core.money import ZERO
from app.reports.base import Report
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.repositories.sales_repositories import PaymentRepository, SalesDocumentRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow

# (column title, smallest days overdue, largest days overdue)
AGING_BUCKETS = [
    ("Current", None, 0),
    ("1 - 30", 1, 30),
    ("31 - 60", 31, 60),
    ("61 - 90", 61, 90),
    ("91 and over", 91, None),
]


def bucket_index(days_overdue: int) -> int:
    for index, (_title, low, high) in enumerate(AGING_BUCKETS):
        if (low is None or days_overdue >= low) and (high is None or days_overdue <= high):
            return index
    return len(AGING_BUCKETS) - 1


class OpenItem:
    """An unpaid invoice or bill, in the shape every report here needs."""

    def __init__(self, kind: str, number: str, party_id: int, party_name: str, doc_date: date, due_date: date, total: Decimal, balance: Decimal, contact: str = ""):
        self.kind = kind
        self.number = number
        self.party_id = party_id
        self.party_name = party_name
        self.doc_date = doc_date
        self.due_date = due_date
        self.total = total
        self.balance = balance
        self.contact = contact


class OpenItems:
    """Unpaid invoices and bills on a date."""

    def __init__(self, invoices: InvoiceRepository, purchases: PurchaseDocumentRepository):
        self.invoices = invoices
        self.purchases = purchases

    def receivables(self, company_id: int, on_date: date, customer_id: int | None = None) -> list[OpenItem]:
        items = []
        for invoice in self.invoices.list_unpaid(company_id):
            if invoice.invoice_date > on_date or (customer_id is not None and invoice.customer_id != customer_id):
                continue
            customer = invoice.customer
            contact = " / ".join(part for part in (customer.phone, customer.email) if part)
            items.append(
                OpenItem("Invoice", invoice.invoice_number, customer.id, customer.display_name, invoice.invoice_date, invoice.due_date, invoice.total, invoice.balance_due, contact)
            )
        items.sort(key=lambda item: (item.party_name, item.due_date))
        return items

    def payables(self, company_id: int, on_date: date, vendor_id: int | None = None) -> list[OpenItem]:
        items = []
        for bill in self.purchases.list_unpaid_bills(company_id, vendor_id):
            if bill.doc_date > on_date:
                continue
            vendor = bill.vendor
            items.append(OpenItem("Bill", bill.doc_number or "", vendor.id, vendor.display_name, bill.doc_date, bill.due_date, bill.total, bill.balance))
        items.sort(key=lambda item: (item.party_name, item.due_date))
        return items


ITEM_COLUMNS = ["Date", "Type", "Num", "Name", "Due date"]


def item_cells(item: OpenItem, on_date: date) -> list[str]:
    return [item.doc_date.strftime("%m/%d/%Y"), item.kind, item.number, item.party_name, item.due_date.strftime("%m/%d/%Y")]


# ---------- aging ----------


class AgingSummaryReport(Report):
    """One row per customer (vendor), one column per age bucket."""

    uses_start_date = False
    side = "receivables"

    def __init__(self, open_items: OpenItems):
        self.open_items = open_items

    def items(self, company_id: int, end_date: date) -> list[OpenItem]:
        if self.side == "receivables":
            return self.open_items.receivables(company_id, end_date)
        return self.open_items.payables(company_id, end_date)

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        per_party = {}
        names = {}
        for item in self.items(company_id, end_date):
            values = per_party.setdefault(item.party_id, [ZERO] * (len(AGING_BUCKETS) + 1))
            names[item.party_id] = item.party_name
            values[bucket_index((end_date - item.due_date).days)] += item.balance
            values[-1] += item.balance
        rows = [ReportRow(label=names[party_id], amount=values[-1], values=values) for party_id, values in sorted(per_party.items(), key=lambda pair: names[pair[0]])]
        section = self.make_section("Customers" if self.side == "receivables" else "Vendors", rows)
        columns = [title for title, _low, _high in AGING_BUCKETS] + ["Total"]
        summary = [ReportRow(label="Total", amount=section.total, values=section.totals)]
        return self.make_result(start_date, end_date, [section], summary, columns=columns, options=options)


class AgingDetailReport(AgingSummaryReport):
    """Each unpaid invoice (bill), grouped by age bucket."""

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        rows_per_bucket = [[] for _bucket in AGING_BUCKETS]
        for item in self.items(company_id, end_date):
            days = (end_date - item.due_date).days
            rows_per_bucket[bucket_index(days)].append(
                ReportRow(label=f"{item.kind} {item.number}", amount=item.balance, cells=item_cells(item, end_date) + [str(max(days, 0))], values=[item.total, item.balance])
            )
        sections = []
        for (title, _low, _high), rows in zip(AGING_BUCKETS, rows_per_bucket):
            heading = title if title == "Current" else title + " days past due"
            sections.append(self.make_section(heading, rows))
        total = sum((section.total for section in sections), ZERO)
        return self.make_result(
            start_date,
            end_date,
            sections,
            [ReportRow(label="Total", amount=total, values=[None, total])],
            columns=["Amount", "Open balance"],
            text_columns=ITEM_COLUMNS + ["Past due"],
            options=options,
        )


class ReceivablesAgingSummaryReport(AgingSummaryReport):
    key = "ar-aging-summary"
    title = "A/R Aging Summary"
    description = "What each customer owes, split by how late it is."
    group = "Who owes you"


class ReceivablesAgingDetailReport(AgingDetailReport):
    key = "ar-aging"
    title = "A/R Aging Detail"
    description = "Each unpaid invoice, grouped by how many days past due it is."
    group = "Who owes you"


class PayablesAgingSummaryReport(AgingSummaryReport):
    key = "ap-aging-summary"
    title = "A/P Aging Summary"
    description = "What you owe each vendor, split by how late it is."
    group = "What you owe"
    side = "payables"


class PayablesAgingDetailReport(AgingDetailReport):
    key = "ap-aging"
    title = "A/P Aging Detail"
    description = "Each unpaid bill, grouped by how many days past due it is."
    group = "What you owe"
    side = "payables"


# ---------- open items ----------


class OpenItemsReport(Report):
    """Every unpaid invoice (bill), grouped by customer (vendor)."""

    uses_start_date = False
    side = "receivables"
    overdue_only = False

    def __init__(self, open_items: OpenItems):
        self.open_items = open_items

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        if self.side == "receivables":
            items = self.open_items.receivables(company_id, end_date, options.customer_id)
        else:
            items = self.open_items.payables(company_id, end_date, options.vendor_id)
        per_party = {}
        for item in items:
            days = (end_date - item.due_date).days
            if self.overdue_only and days <= 0:
                continue
            cells = item_cells(item, end_date) + [str(max(days, 0))]
            if self.overdue_only:
                cells.append(item.contact)
            per_party.setdefault(item.party_name, []).append(
                ReportRow(label=f"{item.kind} {item.number}", amount=item.balance, cells=cells, values=[item.total, item.balance])
            )
        sections = []
        for name in sorted(per_party):
            section = self.make_section(name, per_party[name])
            sections.append(section)
        total = sum((section.total for section in sections), ZERO)
        text_columns = ITEM_COLUMNS + ["Past due"] + (["Phone / email"] if self.overdue_only else [])
        return self.make_result(
            start_date,
            end_date,
            sections,
            [ReportRow(label="Total", amount=total, values=[None, total])],
            columns=["Amount", "Open balance"],
            text_columns=text_columns,
            options=options,
        )


class OpenInvoicesReport(OpenItemsReport):
    key = "open-invoices"
    title = "Open Invoices"
    description = "Every invoice that is not fully paid, by customer."
    group = "Who owes you"
    options = ["customer_id"]


class CollectionsReport(OpenItemsReport):
    key = "collections"
    title = "Collections Report"
    description = "Overdue invoices with each customer's phone and email, to follow up."
    group = "Who owes you"
    overdue_only = True
    options = ["customer_id"]


class UnpaidBillsReport(OpenItemsReport):
    key = "unpaid-bills"
    title = "Unpaid Bills"
    description = "Every bill that is not fully paid, by vendor."
    group = "What you owe"
    side = "payables"
    options = ["vendor_id"]


# ---------- balances ----------


class CustomerBalanceSummaryReport(Report):
    key = "customer-balance-summary"
    title = "Customer Balance Summary"
    description = "What each customer owes: unpaid invoices less unused credits."
    group = "Who owes you"
    uses_start_date = False

    def __init__(self, invoices: InvoiceRepository, sales_documents: SalesDocumentRepository, payments: PaymentRepository, names):
        self.invoices = invoices
        self.sales_documents = sales_documents
        self.payments = payments
        self.names = names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        balances = dict(self.invoices.open_balance_by_customer(company_id))
        for customer_id, credit in self.sales_documents.open_credit_by_customer(company_id).items():
            balances[customer_id] = balances.get(customer_id, ZERO) - credit
        for customer_id, unapplied in self.payments.unapplied_by_customer(company_id).items():
            balances[customer_id] = balances.get(customer_id, ZERO) - unapplied
        names = self.names.for_kind(company_id, "customer")
        rows = [ReportRow(label=names.get(customer_id, ""), amount=amount) for customer_id, amount in balances.items() if amount != 0]
        rows.sort(key=lambda row: row.label)
        section = self.make_section("Customers", rows)
        return self.make_result(start_date, end_date, [section], [ReportRow(label="Total", amount=section.total)], options=options)


class CustomerBalanceDetailReport(OpenItemsReport):
    key = "customer-balance-detail"
    title = "Customer Balance Detail"
    description = "The unpaid invoices behind each customer's balance."
    group = "Who owes you"
    options = ["customer_id"]


class VendorBalanceSummaryReport(Report):
    key = "vendor-balance-summary"
    title = "Vendor Balance Summary"
    description = "What you owe each vendor: unpaid bills less unused vendor credits."
    group = "What you owe"
    uses_start_date = False

    def __init__(self, purchases: PurchaseDocumentRepository, names):
        self.purchases = purchases
        self.names = names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        names = self.names.for_kind(company_id, "vendor")
        rows = [ReportRow(label=names.get(vendor_id, ""), amount=amount) for vendor_id, amount in self.purchases.open_balance_by_vendor(company_id).items() if amount != 0]
        rows.sort(key=lambda row: row.label)
        section = self.make_section("Vendors", rows)
        return self.make_result(start_date, end_date, [section], [ReportRow(label="Total", amount=section.total)], options=options)


class VendorBalanceDetailReport(OpenItemsReport):
    key = "vendor-balance-detail"
    title = "Vendor Balance Detail"
    description = "The unpaid bills behind each vendor's balance."
    group = "What you owe"
    side = "payables"
    options = ["vendor_id"]
