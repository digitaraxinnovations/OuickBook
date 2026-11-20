"""
Sales and expense summaries.

- Sales by Customer Summary:        income per customer (accrual or cash).
- Sales by Product/Service Summary: quantity and amount per item from invoices
                                    and sales receipts, less credit memos and refunds.
- Expenses by Vendor Summary:       expenses per vendor (accrual or cash).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.money import ZERO
from app.models import Invoice, InvoiceLine, Product, SalesDocument, SalesDocumentLine
from app.models.enums import AccountType, InvoiceStatus, SalesDocStatus, SalesDocType
from app.reports.base import Report
from app.reports.report_data import LedgerFacts, ListNames, filter_facts
from app.schemas.report import ReportOptions, ReportResult, ReportRow

NOT_SPECIFIED = "Not specified"
SALE_TYPES = (SalesDocType.SALES_RECEIPT,)
RETURN_TYPES = (SalesDocType.CREDIT_MEMO, SalesDocType.REFUND_RECEIPT)


class PartySummaryReport(Report):
    """Income (or expense) facts added up per customer (or vendor)."""

    options = ["basis", "class_id", "location_id"]
    account_type = AccountType.INCOME
    party = "customer"

    def __init__(self, facts: LedgerFacts, names: ListNames):
        self.facts = facts
        self.names = names

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        start = start_date or date(end_date.year, 1, 1)
        facts = filter_facts(self.facts.profit_and_loss(company_id, start, end_date, options.basis), options)
        names = self.names.for_kind(company_id, self.party)
        totals = {}
        for fact in facts:
            if fact.account.account_type != self.account_type:
                continue
            party_id = fact.customer_id if self.party == "customer" else fact.vendor_id
            amount = fact.amount if self.account_type == AccountType.INCOME else -fact.amount
            totals[party_id] = totals.get(party_id, ZERO) + amount
        rows = []
        for party_id, amount in totals.items():
            if amount == 0:
                continue
            label = names.get(party_id, NOT_SPECIFIED) if party_id is not None else NOT_SPECIFIED
            rows.append(ReportRow(label=label, amount=amount))
        rows.sort(key=lambda row: (row.label == NOT_SPECIFIED, row.label))
        section = self.make_section("Customers" if self.party == "customer" else "Vendors", rows)
        return self.make_result(start_date, end_date, [section], [ReportRow(label="Total", amount=section.total)], options=options)


class SalesByCustomerReport(PartySummaryReport):
    key = "sales-by-customer"
    title = "Sales by Customer Summary"
    description = "Your income from each customer."
    group = "Sales and customers"


class ExpensesByVendorReport(PartySummaryReport):
    key = "expenses-by-vendor"
    title = "Expenses by Vendor Summary"
    description = "What you spent with each vendor."
    group = "Expenses and vendors"
    account_type = AccountType.EXPENSE
    party = "vendor"


class SalesByProductReport(Report):
    key = "sales-by-product"
    title = "Sales by Product/Service Summary"
    description = "Quantity sold and income for each product and service."
    group = "Sales and customers"
    options = ["customer_id"]

    def __init__(self, session):
        self.session = session

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        start = start_date or date(end_date.year, 1, 1)
        # per_item[product id] = [quantity, amount]
        per_item = {}

        invoice_lines = (
            select(InvoiceLine)
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .where(
                Invoice.company_id == company_id,
                Invoice.status != InvoiceStatus.VOID,
                Invoice.invoice_date >= start,
                Invoice.invoice_date <= end_date,
            )
        )
        if options.customer_id is not None:
            invoice_lines = invoice_lines.where(Invoice.customer_id == options.customer_id)
        for line in self.session.scalars(invoice_lines):
            self.add(per_item, line.product_id, line.quantity, line.amount)

        document_lines = (
            select(SalesDocumentLine, SalesDocument.doc_type)
            .join(SalesDocument, SalesDocument.id == SalesDocumentLine.document_id)
            .where(
                SalesDocument.company_id == company_id,
                SalesDocument.status != SalesDocStatus.VOID,
                SalesDocument.doc_type.in_(SALE_TYPES + RETURN_TYPES),
                SalesDocument.doc_date >= start,
                SalesDocument.doc_date <= end_date,
            )
        )
        if options.customer_id is not None:
            document_lines = document_lines.where(SalesDocument.customer_id == options.customer_id)
        for line, doc_type in self.session.execute(document_lines):
            sign = Decimal("-1") if doc_type in RETURN_TYPES else Decimal("1")
            self.add(per_item, line.product_id, line.quantity * sign, line.amount * sign)

        names = {}
        for product_id, name in self.session.execute(select(Product.id, Product.name).where(Product.company_id == company_id)):
            names[product_id] = name

        rows = []
        for product_id, (quantity, amount) in per_item.items():
            label = names.get(product_id, "No product (description only)") if product_id else "No product (description only)"
            average = (amount / quantity).quantize(Decimal("0.01")) if quantity else None
            rows.append(ReportRow(label=label, amount=amount, values=[quantity, amount, average]))
        rows.sort(key=lambda row: row.label)
        section = self.make_section("Products and services", rows)
        section.totals = [None, section.total, None]
        return self.make_result(
            start_date,
            end_date,
            [section],
            [ReportRow(label="Total", amount=section.total, values=[None, section.total, None])],
            columns=["Quantity", "Amount", "Average price"],
            options=options,
            notes=["Amounts are before discounts and sales tax."],
        )

    def add(self, per_item: dict, product_id, quantity: Decimal, amount: Decimal) -> None:
        values = per_item.setdefault(product_id, [ZERO, ZERO])
        values[0] += quantity
        values[1] += amount
