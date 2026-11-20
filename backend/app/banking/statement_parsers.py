"""
Reads bank statement files into a simple list of lines.

- CSV: any bank's export. Columns are found from the header row
  (date / description / amount, or separate debit and credit columns).
- OFX and QFX: the standard "Web Connect" download most banks offer.

To support another format, add a parser class with a parse() method
and return it from parser_for().
"""

import csv
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import BusinessRuleError
from app.core.money import to_money

COMMON_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%b %d, %Y"]

# Header names banks use for each column (lowercase).
DATE_HEADERS = ["date", "transaction date", "posted date", "posting date", "trans date"]
DESCRIPTION_HEADERS = ["description", "payee", "name", "memo", "details", "narrative"]
AMOUNT_HEADERS = ["amount", "transaction amount"]
DEBIT_HEADERS = ["debit", "withdrawal", "withdrawals", "money out", "paid out"]
CREDIT_HEADERS = ["credit", "deposit", "deposits", "money in", "paid in"]


class StatementLine:
    def __init__(self, txn_date: date, description: str, amount: Decimal, external_id: str):
        self.txn_date = txn_date
        self.description = description
        self.amount = amount
        self.external_id = external_id


def fingerprint(txn_date: date, amount: Decimal, description: str, occurrence: int) -> str:
    """A stable id for a line without a bank id, so the same file imported twice is ignored."""
    text = f"{txn_date.isoformat()}|{amount}|{description.strip().lower()}|{occurrence}"
    return "fp-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:32]


def parse_amount(text: str | None) -> Decimal | None:
    if text is None:
        return None
    cleaned = text.strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    if cleaned == "":
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise BusinessRuleError(f'"{text}" is not an amount.')
    return -value if negative else value


def parse_date(text: str, date_format: str | None) -> date:
    text = text.strip()
    formats = [date_format] if date_format else COMMON_DATE_FORMATS
    for one_format in formats:
        try:
            return datetime.strptime(text, one_format).date()
        except ValueError:
            continue
    raise BusinessRuleError(f'Could not read the date "{text}". Choose the date format.')


def find_column(headers: list[str], chosen: str | None, candidates: list[str]) -> str | None:
    if chosen:
        if chosen not in headers:
            raise BusinessRuleError(f'The file has no column named "{chosen}".')
        return chosen
    for header in headers:
        if header.strip().lower() in candidates:
            return header
    return None


class CsvStatementParser:
    def __init__(self, date_column=None, description_column=None, amount_column=None, debit_column=None,
                 credit_column=None, date_format=None, reverse_signs=False):
        self.date_column = date_column
        self.description_column = description_column
        self.amount_column = amount_column
        self.debit_column = debit_column
        self.credit_column = credit_column
        self.date_format = date_format
        self.reverse_signs = reverse_signs

    def parse(self, content: str) -> list[StatementLine]:
        reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
        headers = reader.fieldnames or []
        date_col = find_column(headers, self.date_column, DATE_HEADERS)
        description_col = find_column(headers, self.description_column, DESCRIPTION_HEADERS)
        amount_col = find_column(headers, self.amount_column, AMOUNT_HEADERS)
        debit_col = find_column(headers, self.debit_column, DEBIT_HEADERS)
        credit_col = find_column(headers, self.credit_column, CREDIT_HEADERS)

        if date_col is None or description_col is None:
            raise BusinessRuleError("Could not find the date and description columns. Choose them by name.")
        if amount_col is None and debit_col is None and credit_col is None:
            raise BusinessRuleError("Could not find an amount column (or debit / credit columns). Choose it by name.")

        lines = []
        seen = {}
        for row in reader:
            if not row.get(date_col):
                continue
            if amount_col is not None:
                amount = parse_amount(row.get(amount_col)) or Decimal("0")
            else:
                money_out = parse_amount(row.get(debit_col)) if debit_col else None
                money_in = parse_amount(row.get(credit_col)) if credit_col else None
                amount = (money_in or Decimal("0")) - abs(money_out or Decimal("0"))
            if self.reverse_signs:
                amount = -amount
            amount = to_money(amount)
            if amount == 0:
                continue

            txn_date = parse_date(row[date_col], self.date_format)
            description = (row.get(description_col) or "").strip() or "(no description)"
            key = (txn_date, amount, description.lower())
            seen[key] = seen.get(key, 0) + 1
            lines.append(StatementLine(txn_date, description[:500], amount, fingerprint(txn_date, amount, description, seen[key])))
        return lines


class OfxStatementParser:
    """OFX / QFX files. Handles both the old SGML style (no closing tags) and the XML style."""

    def parse(self, content: str) -> list[StatementLine]:
        blocks = re.split(r"<STMTTRN>", content, flags=re.IGNORECASE)[1:]
        if not blocks:
            raise BusinessRuleError("No transactions were found in this OFX/QFX file.")
        lines = []
        for block in blocks:
            block = re.split(r"</STMTTRN>", block, flags=re.IGNORECASE)[0]
            amount = parse_amount(self.tag(block, "TRNAMT"))
            posted = self.tag(block, "DTPOSTED")
            if amount is None or not posted:
                continue
            txn_date = datetime.strptime(posted[:8], "%Y%m%d").date()
            name = self.tag(block, "NAME") or ""
            memo = self.tag(block, "MEMO") or ""
            description = name if name else memo
            if name and memo and memo.lower() not in name.lower():
                description = name + " - " + memo
            external_id = self.tag(block, "FITID") or fingerprint(txn_date, amount, description, len(lines))
            lines.append(StatementLine(txn_date, (description or "(no description)")[:500], to_money(amount), external_id[:100]))
        return lines

    def tag(self, block: str, name: str) -> str | None:
        match = re.search(r"<" + name + r">([^<\r\n]*)", block, flags=re.IGNORECASE)
        if match is None:
            return None
        return match.group(1).strip()


def parser_for(filename: str, options) -> object:
    lower = filename.lower()
    if lower.endswith(".ofx") or lower.endswith(".qfx") or lower.endswith(".qbo"):
        return OfxStatementParser()
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return CsvStatementParser(
            date_column=options.date_column,
            description_column=options.description_column,
            amount_column=options.amount_column,
            debit_column=options.debit_column,
            credit_column=options.credit_column,
            date_format=options.date_format,
            reverse_signs=options.reverse_signs,
        )
    raise BusinessRuleError("Upload a CSV, OFX or QFX file.")
