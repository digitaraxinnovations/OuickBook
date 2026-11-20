"""
Turns invoices, other sales forms and statements into a PdfDocument
that DocumentPdfBuilder can draw.
"""

from decimal import Decimal

from app.documents.pdf_builder import CONTENT_WIDTH, PdfDocument, TableColumn
from app.models import Company, Invoice, SalesDocument
from app.models.enums import SalesDocType
from app.schemas.sales_extras import StatementResult

CURRENCY_SYMBOLS = {"USD": "$", "CAD": "$", "AUD": "$", "GBP": "£", "INR": "Rs "}

DOCUMENT_TITLES = {
    SalesDocType.ESTIMATE: "Estimate",
    SalesDocType.SALES_RECEIPT: "Sales Receipt",
    SalesDocType.CREDIT_MEMO: "Credit Memo",
    SalesDocType.REFUND_RECEIPT: "Refund Receipt",
    SalesDocType.DELAYED_CHARGE: "Delayed Charge",
    SalesDocType.DELAYED_CREDIT: "Delayed Credit",
}


def money(amount, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    value = Decimal(amount)
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def nice_date(value) -> str:
    if value is None:
        return ""
    return value.strftime("%b %d, %Y")


def quantity_text(value) -> str:
    value = Decimal(value)
    if value == value.to_integral_value():
        return str(int(value))
    return str(value.normalize())


def line_columns() -> list[TableColumn]:
    return [
        TableColumn("Description", CONTENT_WIDTH - 95),
        TableColumn("Qty", 20, "R"),
        TableColumn("Rate", 35, "R"),
        TableColumn("Amount", 40, "R"),
    ]


def bill_to(customer) -> list[str]:
    lines = [customer.display_name]
    if customer.company_name and customer.company_name != customer.display_name:
        lines.append(customer.company_name)
    if customer.address:
        lines.extend(customer.address.splitlines())
    if customer.email:
        lines.append(customer.email)
    return lines


def add_amount_rows(document: PdfDocument, record, currency: str) -> None:
    """Subtotal, discount, shipping and tax rows (only when used)."""
    if record.discount_amount > 0 or record.shipping_amount > 0 or record.tax_amount != 0:
        document.total_rows.append(("Subtotal", money(record.subtotal, currency), False))
    if record.discount_amount > 0:
        label = "Discount"
        if record.discount_type is not None and record.discount_type.value == "PERCENT":
            label = f"Discount ({quantity_text(record.discount_value)}%)"
        document.total_rows.append((label, money(-record.discount_amount, currency), False))
    if record.shipping_amount > 0:
        document.total_rows.append(("Shipping", money(record.shipping_amount, currency), False))
    if record.tax_code_id is not None:
        document.total_rows.append(("Sales tax", money(record.tax_amount, currency), False))


def invoice_document(invoice: Invoice, company: Company) -> PdfDocument:
    currency = company.currency
    document = PdfDocument("Invoice")
    document.number = invoice.invoice_number
    document.info_rows = [
        ("Invoice date", nice_date(invoice.invoice_date)),
        ("Due date", nice_date(invoice.due_date)),
    ]
    if invoice.status.value in ("PAID", "VOID"):
        document.status_stamp = invoice.status.value
    document.bill_to_lines = bill_to(invoice.customer)
    document.columns = line_columns()
    for line in invoice.lines:
        document.rows.append([line.description or "", quantity_text(line.quantity), money(line.rate, currency), money(line.amount, currency)])

    add_amount_rows(document, invoice, currency)
    document.total_rows.append(("Total", money(invoice.total, currency), True))
    if invoice.amount_paid > 0:
        document.total_rows.append(("Payments", money(-invoice.amount_paid, currency), False))
    document.total_rows.append(("Balance due", money(invoice.balance_due, currency), True))
    document.note = invoice.memo or ""
    return document


def sales_document(record: SalesDocument, company: Company) -> PdfDocument:
    currency = company.currency
    document = PdfDocument(DOCUMENT_TITLES[record.doc_type])
    document.number = record.doc_number
    document.info_rows = [("Date", nice_date(record.doc_date))]
    if record.expiration_date:
        document.info_rows.append(("Expires", nice_date(record.expiration_date)))
    if record.payment_method:
        document.info_rows.append(("Payment method", record.payment_method.value.replace("_", " ").title()))
    if record.status.value in ("VOID", "ACCEPTED", "REJECTED", "CLOSED"):
        document.status_stamp = record.status.value
    document.bill_to_lines = bill_to(record.customer)
    document.columns = line_columns()
    for line in record.lines:
        document.rows.append([line.description or "", quantity_text(line.quantity), money(line.rate, currency), money(line.amount, currency)])

    add_amount_rows(document, record, currency)
    document.total_rows.append(("Total", money(record.total, currency), True))
    if record.doc_type == SalesDocType.CREDIT_MEMO:
        document.total_rows.append(("Credit remaining", money(record.remaining, currency), True))
    document.note = record.memo or ""
    return document


def statement_document(statement: StatementResult, company: Company) -> PdfDocument:
    currency = company.currency
    document = PdfDocument("Statement")
    period = "As of " + nice_date(statement.end_date)
    if statement.start_date is not None:
        period = nice_date(statement.start_date) + " - " + nice_date(statement.end_date)
    document.info_rows = [
        ("Statement type", statement.statement_type.value.replace("_", " ").title()),
        ("Period", period),
    ]
    document.bill_to_label = "To"
    document.bill_to_lines = [statement.customer_name]
    if statement.customer_address:
        document.bill_to_lines.extend(statement.customer_address.splitlines())

    document.columns = [
        TableColumn("Date", 30),
        TableColumn("Transaction", CONTENT_WIDTH - 140),
        TableColumn("Reference", 30),
        TableColumn("Amount", 40, "R"),
        TableColumn("Balance", 40, "R"),
    ]
    if statement.start_date is not None and statement.statement_type.value == "BALANCE_FORWARD":
        document.rows.append([nice_date(statement.start_date), "Balance forward", "", "", money(statement.opening_balance, currency)])
    for line in statement.lines:
        document.rows.append(
            [nice_date(line.line_date), line.transaction_type, line.reference, money(line.amount, currency), money(line.balance, currency)]
        )
    document.total_rows.append(("Amount due", money(statement.closing_balance, currency), True))
    return document
