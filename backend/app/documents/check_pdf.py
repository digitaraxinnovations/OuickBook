"""
Prints checks on plain paper or standard "check on top" stock:
the check at the top of the page and a stub (voucher) below it.
"""

from datetime import date
from decimal import Decimal

from fpdf import FPDF

from app.core.number_words import amount_in_words
from app.documents.pdf_builder import MARGIN, safe_text
from app.documents.pdf_content import money
from app.models import Company


class CheckData:
    def __init__(self, number: str, check_date: date, payee: str, amount: Decimal, memo: str, bank_name: str):
        self.number = number
        self.check_date = check_date
        self.payee = payee
        self.amount = amount
        self.memo = memo
        self.bank_name = bank_name
        # (description, amount) rows printed on the stub
        self.stub_lines: list[tuple[str, Decimal]] = []


class CheckPdfBuilder:
    def __init__(self, company: Company):
        self.company = company

    def build(self, checks: list[CheckData]) -> bytes:
        pdf = FPDF(format="Letter", unit="mm")
        pdf.set_auto_page_break(auto=False)
        for check in checks:
            pdf.add_page()
            self.draw_check(pdf, check)
            self.draw_stub(pdf, check, top=100)
            self.draw_stub(pdf, check, top=190)
        return bytes(pdf.output())

    def draw_check(self, pdf: FPDF, check: CheckData) -> None:
        currency = self.company.currency
        pdf.set_text_color(30, 30, 30)

        # Company and bank
        pdf.set_xy(MARGIN, 14)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(110, 5, safe_text(self.company.name))
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(70, 5, safe_text(check.number), align="R")
        pdf.set_xy(MARGIN, 19)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(110, 4, safe_text((self.company.address or "").replace("\n", ", ")))
        pdf.cell(70, 4, safe_text(check.bank_name), align="R")

        # Date
        pdf.set_xy(140, 30)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(55, 6, "Date  " + check.check_date.strftime("%m/%d/%Y"), align="R")

        # Pay to the order of ... $ amount
        pdf.set_xy(MARGIN, 42)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(25, 6, "PAY TO THE ORDER OF")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(110, 6, safe_text(check.payee))
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 6, "**" + money(check.amount, currency).replace("-", ""), border=1, align="R")
        pdf.line(MARGIN + 25, 48, 150, 48)

        # Amount in words
        pdf.set_xy(MARGIN, 54)
        pdf.set_font("Helvetica", "", 10)
        words = amount_in_words(check.amount)
        pdf.cell(170, 6, safe_text(words + " " + "*" * max(0, 60 - len(words))))
        pdf.cell(10, 6, "DOLLARS", align="R")
        pdf.line(MARGIN, 60, 195, 60)

        # Memo and signature
        pdf.set_xy(MARGIN, 76)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(12, 5, "MEMO")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(80, 5, safe_text(check.memo))
        pdf.line(MARGIN + 12, 81, 100, 81)
        pdf.line(125, 81, 195, 81)
        pdf.set_xy(125, 82)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(70, 4, "AUTHORIZED SIGNATURE", align="C")

    def draw_stub(self, pdf: FPDF, check: CheckData, top: float) -> None:
        currency = self.company.currency
        pdf.set_draw_color(180, 180, 180)
        pdf.line(MARGIN, top - 4, 195, top - 4)
        pdf.set_xy(MARGIN, top)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(120, 5, safe_text(check.payee))
        pdf.cell(60, 5, safe_text("Check " + check.number + "   " + check.check_date.strftime("%m/%d/%Y")), align="R")
        pdf.set_font("Helvetica", "", 9)
        row_y = top + 8
        for description, amount in check.stub_lines[:10]:
            pdf.set_xy(MARGIN, row_y)
            pdf.cell(140, 5, safe_text(description)[:90])
            pdf.cell(40, 5, money(amount, currency), align="R")
            row_y += 5
        pdf.set_xy(MARGIN, top + 62)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(140, 5, safe_text(check.bank_name))
        pdf.cell(40, 5, money(check.amount, currency), align="R")
