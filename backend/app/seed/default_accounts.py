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
    SALES_TAX_PAYABLE = "sales_tax_payable"
    OWNERS_EQUITY = "owners_equity"
    RETAINED_EARNINGS = "retained_earnings"
    SALES = "sales"
    DISCOUNTS_GIVEN = "discounts_given"
    SHIPPING_INCOME = "shipping_income"
    LATE_FEE_INCOME = "late_fee_income"
    UNCATEGORIZED_EXPENSE = "uncategorized_expense"
    INVENTORY_ASSET = "inventory_asset"
    COST_OF_GOODS_SOLD = "cost_of_goods_sold"
    INVENTORY_SHRINKAGE = "inventory_shrinkage"
    OPENING_BALANCE_EQUITY = "opening_balance_equity"


class DetailType:
    """Detail types the app treats specially."""

    BANK = "Bank"
    CREDIT_CARD = "Credit Card"


# Boxes on the US 1099 forms an expense account can be mapped to.
FORM_1099_BOXES = {
    "NEC_1": "1099-NEC Box 1: Nonemployee compensation",
    "MISC_1": "1099-MISC Box 1: Rents",
    "MISC_2": "1099-MISC Box 2: Royalties",
    "MISC_3": "1099-MISC Box 3: Other income",
    "MISC_6": "1099-MISC Box 6: Medical and health care payments",
    "MISC_10": "1099-MISC Box 10: Gross proceeds paid to an attorney",
}


# Income tax categories (US Schedule C lines). An account mapped to one of
# these appears on that line of the Tax Schedule Summary report.
TAX_LINES = {
    "SCHC_1": "Line 1 - Gross receipts or sales",
    "SCHC_2": "Line 2 - Returns and allowances",
    "SCHC_4": "Line 4 - Cost of goods sold",
    "SCHC_6": "Line 6 - Other income",
    "SCHC_8": "Line 8 - Advertising",
    "SCHC_9": "Line 9 - Car and truck expenses",
    "SCHC_11": "Line 11 - Contract labor",
    "SCHC_13": "Line 13 - Depreciation",
    "SCHC_15": "Line 15 - Insurance (other than health)",
    "SCHC_16B": "Line 16b - Interest (other)",
    "SCHC_17": "Line 17 - Legal and professional services",
    "SCHC_18": "Line 18 - Office expense",
    "SCHC_20B": "Line 20b - Rent or lease (other business property)",
    "SCHC_21": "Line 21 - Repairs and maintenance",
    "SCHC_22": "Line 22 - Supplies",
    "SCHC_23": "Line 23 - Taxes and licenses",
    "SCHC_24A": "Line 24a - Travel",
    "SCHC_24B": "Line 24b - Deductible meals",
    "SCHC_25": "Line 25 - Utilities",
    "SCHC_26": "Line 26 - Wages",
    "SCHC_27A": "Line 27a - Other expenses",
}

# Default income tax category for the starting chart of accounts (by account code).
DEFAULT_TAX_LINES = {
    "4000": "SCHC_1",
    "4100": "SCHC_1",
    "4500": "SCHC_1",
    "4600": "SCHC_6",
    "4800": "SCHC_2",
    "4900": "SCHC_6",
    "5000": "SCHC_4",
    "5100": "SCHC_4",
    "6000": "SCHC_8",
    "6100": "SCHC_27A",
    "6200": "SCHC_15",
    "6300": "SCHC_24B",
    "6400": "SCHC_18",
    "6500": "SCHC_20B",
    "6600": "SCHC_21",
    "6700": "SCHC_24A",
    "6800": "SCHC_25",
    "6900": "SCHC_11",
    "6999": "SCHC_27A",
}


DEFAULT_PAYMENT_TERMS = [
    {"name": "Due on receipt", "due_days": 0},
    {"name": "Net 15", "due_days": 15},
    {"name": "Net 30", "due_days": 30},
    {"name": "Net 60", "due_days": 60},
]


DEFAULT_ACCOUNTS = [
    # ---------- Assets ----------
    {"code": "1000", "name": "Checking", "type": AccountType.ASSET, "detail": DetailType.BANK, "key": SystemAccount.CHECKING},
    {"code": "1010", "name": "Savings", "type": AccountType.ASSET, "detail": DetailType.BANK, "key": None},
    {"code": "1200", "name": "Accounts Receivable (A/R)", "type": AccountType.ASSET, "detail": "Accounts Receivable", "key": SystemAccount.ACCOUNTS_RECEIVABLE},
    {"code": "1300", "name": "Undeposited Funds", "type": AccountType.ASSET, "detail": "Other Current Assets", "key": SystemAccount.UNDEPOSITED_FUNDS},
    {"code": "1400", "name": "Inventory Asset", "type": AccountType.ASSET, "detail": "Inventory", "key": SystemAccount.INVENTORY_ASSET},
    {"code": "1500", "name": "Furniture and Equipment", "type": AccountType.ASSET, "detail": "Fixed Assets", "key": None},
    # ---------- Liabilities ----------
    {"code": "2000", "name": "Accounts Payable (A/P)", "type": AccountType.LIABILITY, "detail": "Accounts Payable", "key": SystemAccount.ACCOUNTS_PAYABLE},
    {"code": "2100", "name": "Credit Card", "type": AccountType.LIABILITY, "detail": DetailType.CREDIT_CARD, "key": None},
    {"code": "2200", "name": "Sales Tax Payable", "type": AccountType.LIABILITY, "detail": "Sales Tax Payable", "key": SystemAccount.SALES_TAX_PAYABLE},
    {"code": "2500", "name": "Loan Payable", "type": AccountType.LIABILITY, "detail": "Long Term Liabilities", "key": None},
    # ---------- Equity ----------
    {"code": "3000", "name": "Owner's Investment", "type": AccountType.EQUITY, "detail": "Owner's Equity", "key": SystemAccount.OWNERS_EQUITY},
    {"code": "3050", "name": "Opening Balance Equity", "type": AccountType.EQUITY, "detail": "Opening Balance Equity", "key": SystemAccount.OPENING_BALANCE_EQUITY},
    {"code": "3100", "name": "Owner's Draw", "type": AccountType.EQUITY, "detail": "Owner's Equity", "key": None},
    {"code": "3900", "name": "Retained Earnings", "type": AccountType.EQUITY, "detail": "Retained Earnings", "key": SystemAccount.RETAINED_EARNINGS},
    # ---------- Income ----------
    {"code": "4000", "name": "Sales", "type": AccountType.INCOME, "detail": "Sales of Product Income", "key": SystemAccount.SALES},
    {"code": "4100", "name": "Services", "type": AccountType.INCOME, "detail": "Service/Fee Income", "key": None},
    {"code": "4500", "name": "Shipping Income", "type": AccountType.INCOME, "detail": "Other Primary Income", "key": SystemAccount.SHIPPING_INCOME},
    {"code": "4600", "name": "Late Fee Income", "type": AccountType.INCOME, "detail": "Other Primary Income", "key": SystemAccount.LATE_FEE_INCOME},
    # A "contra" income account: discounts reduce income, so it normally has a debit balance.
    {"code": "4800", "name": "Discounts Given", "type": AccountType.INCOME, "detail": "Discounts/Refunds Given", "key": SystemAccount.DISCOUNTS_GIVEN},
    {"code": "4900", "name": "Other Income", "type": AccountType.INCOME, "detail": "Other Income", "key": None},
    # ---------- Expenses ----------
    {"code": "5000", "name": "Cost of Goods Sold", "type": AccountType.EXPENSE, "detail": "Cost of Goods Sold", "key": SystemAccount.COST_OF_GOODS_SOLD},
    {"code": "5100", "name": "Inventory Shrinkage", "type": AccountType.EXPENSE, "detail": "Supplies & Materials - COGS", "key": SystemAccount.INVENTORY_SHRINKAGE},
    {"code": "6000", "name": "Advertising & Marketing", "type": AccountType.EXPENSE, "detail": "Advertising/Promotional", "key": None},
    {"code": "6100", "name": "Bank Charges & Fees", "type": AccountType.EXPENSE, "detail": "Bank Charges", "key": None},
    {"code": "6200", "name": "Insurance", "type": AccountType.EXPENSE, "detail": "Insurance", "key": None},
    {"code": "6300", "name": "Meals & Entertainment", "type": AccountType.EXPENSE, "detail": "Entertainment Meals", "key": None},
    {"code": "6400", "name": "Office Supplies & Software", "type": AccountType.EXPENSE, "detail": "Office/General Administrative Expenses", "key": None},
    {"code": "6500", "name": "Rent & Lease", "type": AccountType.EXPENSE, "detail": "Rent or Lease of Buildings", "key": None, "box_1099": "MISC_1"},
    {"code": "6600", "name": "Repairs & Maintenance", "type": AccountType.EXPENSE, "detail": "Repair & Maintenance", "key": None},
    {"code": "6700", "name": "Travel", "type": AccountType.EXPENSE, "detail": "Travel", "key": None},
    {"code": "6800", "name": "Utilities", "type": AccountType.EXPENSE, "detail": "Utilities", "key": None},
    {"code": "6900", "name": "Contractors", "type": AccountType.EXPENSE, "detail": "Cost of Labor", "key": None, "box_1099": "NEC_1"},
    {"code": "6999", "name": "Uncategorized Expense", "type": AccountType.EXPENSE, "detail": "Other Miscellaneous Service Cost", "key": SystemAccount.UNCATEGORIZED_EXPENSE},
]
