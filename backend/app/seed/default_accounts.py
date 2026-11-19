"""
Starting Chart of Accounts for every new company.

This is plain data, not code. To change what a new company gets,
edit this list - no other file needs to change.
"""

from app.models.enums import AccountType


class SystemAccount:
    """Keys for accounts the app must be able to find automatically."""

    CHECKING = "checking"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    UNDEPOSITED_FUNDS = "undeposited_funds"
    ACCOUNTS_PAYABLE = "accounts_payable"
    OWNERS_EQUITY = "owners_equity"
    RETAINED_EARNINGS = "retained_earnings"
    SALES = "sales"
    UNCATEGORIZED_EXPENSE = "uncategorized_expense"


class DetailType:
    """Detail types the app treats specially."""

    BANK = "Bank"
    CREDIT_CARD = "Credit Card"


DEFAULT_ACCOUNTS = [
    # ---------- Assets ----------
    {"code": "1000", "name": "Checking", "type": AccountType.ASSET, "detail": DetailType.BANK, "key": SystemAccount.CHECKING},
    {"code": "1010", "name": "Savings", "type": AccountType.ASSET, "detail": DetailType.BANK, "key": None},
    {"code": "1200", "name": "Accounts Receivable (A/R)", "type": AccountType.ASSET, "detail": "Accounts Receivable", "key": SystemAccount.ACCOUNTS_RECEIVABLE},
    {"code": "1300", "name": "Undeposited Funds", "type": AccountType.ASSET, "detail": "Other Current Assets", "key": SystemAccount.UNDEPOSITED_FUNDS},
    {"code": "1500", "name": "Furniture and Equipment", "type": AccountType.ASSET, "detail": "Fixed Assets", "key": None},
    # ---------- Liabilities ----------
    {"code": "2000", "name": "Accounts Payable (A/P)", "type": AccountType.LIABILITY, "detail": "Accounts Payable", "key": SystemAccount.ACCOUNTS_PAYABLE},
    {"code": "2100", "name": "Credit Card", "type": AccountType.LIABILITY, "detail": DetailType.CREDIT_CARD, "key": None},
    {"code": "2200", "name": "Sales Tax Payable", "type": AccountType.LIABILITY, "detail": "Other Current Liabilities", "key": None},
    {"code": "2500", "name": "Loan Payable", "type": AccountType.LIABILITY, "detail": "Long Term Liabilities", "key": None},
    # ---------- Equity ----------
    {"code": "3000", "name": "Owner's Investment", "type": AccountType.EQUITY, "detail": "Owner's Equity", "key": SystemAccount.OWNERS_EQUITY},
    {"code": "3100", "name": "Owner's Draw", "type": AccountType.EQUITY, "detail": "Owner's Equity", "key": None},
    {"code": "3900", "name": "Retained Earnings", "type": AccountType.EQUITY, "detail": "Retained Earnings", "key": SystemAccount.RETAINED_EARNINGS},
    # ---------- Income ----------
    {"code": "4000", "name": "Sales", "type": AccountType.INCOME, "detail": "Sales of Product Income", "key": SystemAccount.SALES},
    {"code": "4100", "name": "Services", "type": AccountType.INCOME, "detail": "Service/Fee Income", "key": None},
    {"code": "4900", "name": "Other Income", "type": AccountType.INCOME, "detail": "Other Income", "key": None},
    # ---------- Expenses ----------
    {"code": "5000", "name": "Cost of Goods Sold", "type": AccountType.EXPENSE, "detail": "Cost of Goods Sold", "key": None},
    {"code": "6000", "name": "Advertising & Marketing", "type": AccountType.EXPENSE, "detail": "Advertising/Promotional", "key": None},
    {"code": "6100", "name": "Bank Charges & Fees", "type": AccountType.EXPENSE, "detail": "Bank Charges", "key": None},
    {"code": "6200", "name": "Insurance", "type": AccountType.EXPENSE, "detail": "Insurance", "key": None},
    {"code": "6300", "name": "Meals & Entertainment", "type": AccountType.EXPENSE, "detail": "Entertainment Meals", "key": None},
    {"code": "6400", "name": "Office Supplies & Software", "type": AccountType.EXPENSE, "detail": "Office/General Administrative Expenses", "key": None},
    {"code": "6500", "name": "Rent & Lease", "type": AccountType.EXPENSE, "detail": "Rent or Lease of Buildings", "key": None},
    {"code": "6600", "name": "Repairs & Maintenance", "type": AccountType.EXPENSE, "detail": "Repair & Maintenance", "key": None},
    {"code": "6700", "name": "Travel", "type": AccountType.EXPENSE, "detail": "Travel", "key": None},
    {"code": "6800", "name": "Utilities", "type": AccountType.EXPENSE, "detail": "Utilities", "key": None},
    {"code": "6900", "name": "Contractors", "type": AccountType.EXPENSE, "detail": "Cost of Labor", "key": None},
    {"code": "6999", "name": "Uncategorized Expense", "type": AccountType.EXPENSE, "detail": "Other Miscellaneous Service Cost", "key": SystemAccount.UNCATEGORIZED_EXPENSE},
]
