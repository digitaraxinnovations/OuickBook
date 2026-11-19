"""
Every report returns the same simple shape, so the frontend can draw
any report with one generic component.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ReportRow(BaseModel):
    label: str
    amount: Decimal
    account_id: int | None = None


class ReportSection(BaseModel):
    title: str
    rows: list[ReportRow]
    total: Decimal


class ReportResult(BaseModel):
    key: str
    title: str
    start_date: date | None
    end_date: date
    sections: list[ReportSection]
    # Bottom lines such as "Net income" or "Total liabilities and equity".
    summary: list[ReportRow]


class ReportInfo(BaseModel):
    key: str
    title: str
    description: str
    uses_start_date: bool
