from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class AccountBalance(BaseModel):
    account_id: int
    name: str
    balance: Decimal


class DashboardSummary(BaseModel):
    period_start: date
    period_end: date
    income: Decimal
    expenses: Decimal
    net_income: Decimal
    open_invoices_total: Decimal
    open_invoice_count: int
    overdue_invoices_total: Decimal
    overdue_invoice_count: int
    bank_accounts: list[AccountBalance]
