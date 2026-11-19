"""
Draws a business document (invoice, estimate, statement...) as a PDF.

The builder only knows about a generic PdfDocument (title, info boxes,
a table and total rows). pdf_content.py turns invoices, estimates and
statements into a PdfDocument. Adding a new document type therefore never
touches the drawing code.
"""

import io

from fpdf import FPDF

from app.models import Company

PAGE_WIDTH = 210  # A4 in millimetres
MARGIN = 15
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


def safe_text(value) -> str:
    """The built-in PDF fonts only know Latin-1 characters - replace anything else."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("€", "EUR ")
    return text.encode("latin-1", "replace").decode("latin-1")


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


class TableColumn:
    def __init__(self, header: str, width: float, align: str = "L"):
        self.header = header
        self.width = width
        self.align = align


class PdfDocument:
    """Everything one document page needs, as plain text."""

    def __init__(self, title: str):
        self.title = title
        self.number = ""
        # (label, value) pairs shown top right, e.g. ("Date", "Nov 20, 2026")
        self.info_rows: list[tuple[str, str]] = []
        self.bill_to_label = "Bill to"
        self.bill_to_lines: list[str] = []
        self.columns: list[TableColumn] = []
        self.rows: list[list[str]] = []
        # (label, value, is_bold) under the table
        self.total_rows: list[tuple[str, str, bool]] = []
        self.note = ""
        self.status_stamp = ""


class DocumentPdfBuilder:
    def __init__(self, company: Company):
        self.company = company
        self.accent = hex_to_rgb(company.invoice_accent_color or "#059669")
        self.style = company.invoice_template or "classic"

    def build(self, document: PdfDocument) -> bytes:
        pdf = FPDF(format="A4")
        pdf.set_margins(MARGIN, MARGIN, MARGIN)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        self.draw_header(pdf, document)
        self.draw_addresses(pdf, document)
        self.draw_table(pdf, document)
        self.draw_totals(pdf, document)
        self.draw_footer(pdf, document)

        return bytes(pdf.output())

    # ---------- parts of the page ----------

    def draw_header(self, pdf: FPDF, document: PdfDocument) -> None:
        if self.style == "modern":
            pdf.set_fill_color(*self.accent)
            pdf.rect(0, 0, PAGE_WIDTH, 32, style="F")
            title_color = (255, 255, 255)
        elif self.style == "simple":
            title_color = (0, 0, 0)
        else:
            title_color = self.accent

        top = 10 if self.style == "modern" else MARGIN
        if self.company.logo:
            try:
                pdf.image(io.BytesIO(self.company.logo), x=MARGIN, y=top, h=16)
            except Exception:
                pass  # a broken logo should never stop the document

        pdf.set_xy(MARGIN, top)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*title_color)
        pdf.cell(CONTENT_WIDTH, 10, safe_text(document.title.upper()), align="R")
        pdf.ln(9)
        if document.number:
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(CONTENT_WIDTH, 6, safe_text("No. " + document.number), align="R")

        pdf.set_text_color(40, 40, 40)
        pdf.set_y(40 if self.style == "modern" else 36)

        # Company details on the left
        start_y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(100, 6, safe_text(self.company.name))
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        for line in self.company_lines():
            pdf.cell(100, 4.5, safe_text(line))
            pdf.ln(4.5)
        end_left = pdf.get_y()

        # Document info on the right
        pdf.set_y(start_y)
        for label, value in document.info_rows:
            pdf.set_x(PAGE_WIDTH - MARGIN - 80)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(40, 5, safe_text(label), align="R")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(40, 5, safe_text(value), align="R")
            pdf.ln(5)
        if document.status_stamp:
            pdf.set_x(PAGE_WIDTH - MARGIN - 80)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*self.accent)
            pdf.cell(80, 8, safe_text(document.status_stamp.upper()), align="R")
            pdf.set_text_color(40, 40, 40)
            pdf.ln(8)

        pdf.set_y(max(end_left, pdf.get_y()) + 6)

    def company_lines(self) -> list[str]:
        lines = []
        if self.company.address:
            lines.extend(self.company.address.splitlines())
        for value in (self.company.phone, self.company.email, self.company.website):
            if value:
                lines.append(value)
        return lines

    def draw_addresses(self, pdf: FPDF, document: PdfDocument) -> None:
        if not document.bill_to_lines:
            return
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*self.label_color())
        pdf.cell(100, 5, safe_text(document.bill_to_label.upper()))
        pdf.ln(5)
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "", 10)
        for line in document.bill_to_lines:
            pdf.cell(100, 5, safe_text(line))
            pdf.ln(5)
        pdf.ln(5)

    def draw_table(self, pdf: FPDF, document: PdfDocument) -> None:
        # Header row
        if self.style == "simple":
            pdf.set_fill_color(235, 235, 235)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_fill_color(*self.accent)
            pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        for column in document.columns:
            pdf.cell(column.width, 8, safe_text(column.header), align=column.align, fill=True)
        pdf.ln(8)

        # Body rows
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_draw_color(225, 225, 225)
        for row in document.rows:
            for index, column in enumerate(document.columns):
                text = row[index] if index < len(row) else ""
                pdf.cell(column.width, 7, safe_text(text)[:90], border="B", align=column.align)
            pdf.ln(7)
        pdf.ln(3)

    def draw_totals(self, pdf: FPDF, document: PdfDocument) -> None:
        for label, value, is_bold in document.total_rows:
            pdf.set_x(PAGE_WIDTH - MARGIN - 80)
            pdf.set_font("Helvetica", "B" if is_bold else "", 11 if is_bold else 9)
            pdf.cell(45, 6, safe_text(label), align="R")
            pdf.cell(35, 6, safe_text(value), align="R")
            pdf.ln(6)

    def draw_footer(self, pdf: FPDF, document: PdfDocument) -> None:
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        if document.note:
            pdf.multi_cell(CONTENT_WIDTH, 5, safe_text(document.note))
            pdf.ln(2)
        if self.company.invoice_footer:
            pdf.set_text_color(*self.label_color())
            pdf.multi_cell(CONTENT_WIDTH, 5, safe_text(self.company.invoice_footer), align="C")

    def label_color(self) -> tuple[int, int, int]:
        if self.style == "simple":
            return (90, 90, 90)
        return self.accent
