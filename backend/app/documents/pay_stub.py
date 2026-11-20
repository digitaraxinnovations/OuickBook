"""Turns a paycheck into a pay stub that DocumentPdfBuilder can draw."""

from app.documents.pdf_builder import PdfDocument
from app.documents.pdf_content import line_columns, money, nice_date, quantity_text
from app.models import Company, Paycheck
from app.models.enums import PayItemKind

SECTION_NAMES = {
    PayItemKind.DEDUCTION: "Deduction",
    PayItemKind.EMPLOYEE_TAX: "Tax",
    PayItemKind.EMPLOYER_TAX: "Employer tax (paid by company)",
    PayItemKind.EMPLOYER_CONTRIBUTION: "Employer contribution (paid by company)",
}


def pay_stub_document(paycheck: Paycheck, company: Company) -> PdfDocument:
    currency = company.currency
    run = paycheck.run
    document = PdfDocument("Pay Stub")
    document.number = paycheck.check_number or ""
    document.info_rows = [
        ("Pay date", nice_date(run.pay_date)),
        ("Pay period", f"{nice_date(run.period_start)} - {nice_date(run.period_end)}"),
        ("Paid by", "Direct deposit" if paycheck.payment_method.value == "DIRECT_DEPOSIT" else "Check"),
    ]
    if run.status.value == "VOID":
        document.status_stamp = "VOID"
    document.bill_to_label = "Employee"
    document.bill_to_lines = [paycheck.employee.display_name]
    if paycheck.employee.address:
        document.bill_to_lines.extend(paycheck.employee.address.splitlines())

    document.columns = line_columns()
    for line in paycheck.lines:
        description = line.description
        if line.kind in SECTION_NAMES:
            description = f"{SECTION_NAMES[line.kind]}: {line.description}"
        hours = quantity_text(line.hours) if line.hours is not None else ""
        rate = money(line.rate, currency) if line.rate is not None else ""
        amount = line.amount
        if line.kind in (PayItemKind.DEDUCTION, PayItemKind.EMPLOYEE_TAX):
            amount = -amount
        document.rows.append([description, hours, rate, money(amount, currency)])

    document.total_rows.append(("Gross pay", money(paycheck.gross_pay, currency), False))
    document.total_rows.append(("Deductions", money(-paycheck.employee_deductions, currency), False))
    document.total_rows.append(("Taxes", money(-paycheck.employee_taxes, currency), False))
    document.total_rows.append(("Net pay", money(paycheck.net_pay, currency), True))
    return document
