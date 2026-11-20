"""
Turns a ReportResult into a file: CSV, Excel (.xlsx) or PDF.

ReportExporter is the interface; add a new format by writing a class with
`file_extension`, `media_type` and `export()`, and adding it to EXPORTERS.
"""

import csv
import io
from abc import ABC, abstractmethod
from decimal import Decimal

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font

from app.schemas.report import ReportResult, ReportRow


def value_columns(result: ReportResult) -> list[str]:
    return result.columns or ["Amount"]


def row_values(result: ReportResult, row: ReportRow) -> list[Decimal | None]:
    return row.values if result.columns else [row.amount]


def period_text(result: ReportResult) -> str:
    if result.start_date:
        return f"{result.start_date:%b %d, %Y} - {result.end_date:%b %d, %Y}"
    return f"As of {result.end_date:%b %d, %Y}"


def table_rows(result: ReportResult) -> list[tuple[str, list[str], list, bool]]:
    """(label, text cells, values, is_bold) for every printed line, in order."""
    blank_cells = [""] * len(result.text_columns)
    lines = []
    for section in result.sections:
        lines.append((section.title, blank_cells, [None] * len(value_columns(result)), True))
        for row in section.rows:
            cells = row.cells if row.cells else blank_cells
            lines.append(("    " + row.label, cells, row_values(result, row), False))
        totals = section.totals if result.columns else [section.total]
        lines.append(("Total " + section.title, blank_cells, totals, True))
    for row in result.summary:
        lines.append((row.label, blank_cells, row_values(result, row), True))
    return lines


def sheet_title(title: str) -> str:
    """Excel sheet names cannot contain brackets, colons, stars, question marks or slashes (max 31 characters)."""
    for character in "[]:*?/\\":
        title = title.replace(character, "-")
    return title[:31]


def format_value(value, kind: str) -> str:
    if value is None:
        return ""
    if kind == "percent":
        return f"{Decimal(value):,.2f}%"
    if kind == "number":
        return f"{Decimal(value).normalize():f}"
    return f"{Decimal(value):,.2f}"


class ReportExporter(ABC):
    file_extension = ""
    media_type = ""

    @abstractmethod
    def export(self, result: ReportResult, company_name: str) -> bytes:
        """The file's bytes."""


class CsvExporter(ReportExporter):
    file_extension = "csv"
    media_type = "text/csv"

    def export(self, result: ReportResult, company_name: str) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([company_name])
        writer.writerow([result.title])
        writer.writerow([period_text(result) + f" ({result.basis} basis)"])
        writer.writerow([])
        writer.writerow([""] + result.text_columns + value_columns(result))
        for label, cells, values, _bold in table_rows(result):
            writer.writerow([label.strip()] + list(cells) + ["" if value is None else str(value) for value in values])
        for note in result.notes:
            writer.writerow([note])
        return output.getvalue().encode("utf-8-sig")


class ExcelExporter(ReportExporter):
    file_extension = "xlsx"
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def export(self, result: ReportResult, company_name: str) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = sheet_title(result.title)
        bold = Font(bold=True)
        sheet.append([company_name])
        sheet.append([result.title])
        sheet.append([period_text(result)])
        sheet.append([])
        sheet.append([""] + result.text_columns + value_columns(result))
        for cell in sheet[5]:
            cell.font = bold
        kinds = result.column_kinds or ["money"] * len(value_columns(result))
        first_value_column = 2 + len(result.text_columns)
        for label, cells, values, is_bold in table_rows(result):
            sheet.append([label.strip()] + list(cells) + [None if value is None else float(value) for value in values])
            row_number = sheet.max_row
            for index, kind in enumerate(kinds):
                cell = sheet.cell(row=row_number, column=first_value_column + index)
                cell.number_format = "0.00\\%" if kind == "percent" else ("#,##0.00" if kind == "money" else "General")
            if is_bold:
                for cell in sheet[row_number]:
                    cell.font = bold
        sheet.column_dimensions["A"].width = 40
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()


class PdfExporter(ReportExporter):
    file_extension = "pdf"
    media_type = "application/pdf"

    def export(self, result: ReportResult, company_name: str) -> bytes:
        columns = value_columns(result)
        wide = len(columns) + len(result.text_columns) > 4
        pdf = FPDF(orientation="L" if wide else "P", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        width = pdf.w - pdf.l_margin - pdf.r_margin

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(width, 7, self.text(company_name), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(width, 6, self.text(result.title), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(width, 5, self.text(period_text(result) + f" ({result.basis} basis)"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        value_width = 26
        text_width = 24
        label_width = width - value_width * len(columns) - text_width * len(result.text_columns)
        kinds = result.column_kinds or ["money"] * len(columns)

        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(label_width, 6, "", border="B")
        for heading in result.text_columns:
            pdf.cell(text_width, 6, self.text(heading), border="B")
        for heading in columns:
            pdf.cell(value_width, 6, self.text(heading[:18]), border="B", align="R")
        pdf.ln()

        for label, cells, values, is_bold in table_rows(result):
            pdf.set_font("Helvetica", "B" if is_bold else "", 8)
            pdf.cell(label_width, 5, self.text(label)[:70])
            for cell in cells:
                pdf.cell(text_width, 5, self.text(cell)[:16])
            for index, value in enumerate(values):
                pdf.cell(value_width, 5, format_value(value, kinds[index] if index < len(kinds) else "money"), align="R")
            pdf.ln()
        for note in result.notes:
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(width, 5, self.text(note), new_x="LMARGIN", new_y="NEXT")
        return bytes(pdf.output())

    def text(self, value: str) -> str:
        """The built-in PDF fonts only know Latin-1 characters."""
        return value.encode("latin-1", "replace").decode("latin-1")


EXPORTERS = {"csv": CsvExporter(), "xlsx": ExcelExporter(), "pdf": PdfExporter()}
