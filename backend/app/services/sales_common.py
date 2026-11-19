"""
Code shared by every sales form (invoice, estimate, sales receipt, credit memo...):

- SalesLineBuilder   turns the lines the user typed into database line values
- calculate_totals   subtotal, discount, shipping and total
- income_ledger_lines the "income side" of the journal entry
"""

from decimal import Decimal

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.models.enums import DiscountType
from app.repositories.product_repository import ProductRepository
from app.schemas.invoice import InvoiceLineCreate
from app.seed.default_accounts import SystemAccount
from app.services.ledger_service import LedgerLine
from app.services.system_accounts import SystemAccounts


class SalesLineValues:
    """The values of one line, ready to copy onto InvoiceLine or SalesDocumentLine."""

    def __init__(self, product_id, income_account_id, description, quantity, rate, amount):
        self.product_id = product_id
        self.income_account_id = income_account_id
        self.description = description
        self.quantity = quantity
        self.rate = rate
        self.amount = amount

    def as_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "income_account_id": self.income_account_id,
            "description": self.description,
            "quantity": self.quantity,
            "rate": self.rate,
            "amount": self.amount,
        }


class SalesLineBuilder:
    def __init__(self, product_repository: ProductRepository, system_accounts: SystemAccounts):
        self.product_repository = product_repository
        self.system_accounts = system_accounts

    def build(self, company_id: int, line_inputs: list[InvoiceLineCreate]) -> list[SalesLineValues]:
        sales_account = self.system_accounts.get(company_id, SystemAccount.SALES)
        result = []
        for data in line_inputs:
            description = data.description
            income_account_id = sales_account.id

            if data.product_id is not None:
                product = self.product_repository.get(company_id, data.product_id)
                if product is None:
                    raise BusinessRuleError(f"Product {data.product_id} does not exist.")
                income_account_id = product.income_account_id
                if description is None:
                    description = product.description or product.name

            result.append(
                SalesLineValues(
                    product_id=data.product_id,
                    income_account_id=income_account_id,
                    description=description,
                    quantity=data.quantity,
                    rate=data.rate,
                    amount=to_money(data.quantity * data.rate),
                )
            )
        return result


class SalesTotals:
    def __init__(self, subtotal: Decimal, discount_amount: Decimal, shipping_amount: Decimal):
        self.subtotal = subtotal
        self.discount_amount = discount_amount
        self.shipping_amount = shipping_amount
        self.total = subtotal - discount_amount + shipping_amount


def calculate_totals(
    lines: list,
    discount_type: DiscountType | None,
    discount_value: Decimal,
    shipping_amount: Decimal,
) -> SalesTotals:
    """`lines` can be SalesLineValues or database line objects - anything with `.amount`."""
    subtotal = ZERO
    for line in lines:
        subtotal += line.amount

    discount = ZERO
    if discount_type == DiscountType.PERCENT:
        if discount_value > 100:
            raise BusinessRuleError("A percentage discount cannot be more than 100%.")
        discount = to_money(subtotal * discount_value / 100)
    elif discount_type == DiscountType.AMOUNT:
        discount = to_money(discount_value)

    if discount > subtotal:
        raise BusinessRuleError("The discount cannot be more than the subtotal.")

    return SalesTotals(subtotal, discount, to_money(shipping_amount))


def income_ledger_lines(
    company_id: int,
    lines: list,
    totals: SalesTotals,
    system_accounts: SystemAccounts,
    is_return: bool,
) -> list[LedgerLine]:
    """
    The income side of a sales journal entry.

    For a sale:   credit income, debit Discounts Given, credit Shipping Income.
    For a return (credit memo, refund): exactly the opposite.
    The caller adds the other side (Accounts Receivable, bank...).
    """
    # Add up line amounts per income account.
    amount_per_account = {}
    for line in lines:
        current = amount_per_account.get(line.income_account_id, ZERO)
        amount_per_account[line.income_account_id] = current + line.amount

    # For a sale a positive amount is a credit. A return flips every sign.
    signed_amounts = []
    for account_id, amount in amount_per_account.items():
        signed_amounts.append((account_id, amount))
    if totals.discount_amount > 0:
        discount_account = system_accounts.get(company_id, SystemAccount.DISCOUNTS_GIVEN)
        signed_amounts.append((discount_account.id, -totals.discount_amount))
    if totals.shipping_amount > 0:
        shipping_account = system_accounts.get(company_id, SystemAccount.SHIPPING_INCOME)
        signed_amounts.append((shipping_account.id, totals.shipping_amount))

    ledger_lines = []
    for account_id, amount in signed_amounts:
        if is_return:
            amount = -amount
        if amount > 0:
            ledger_lines.append(LedgerLine(account_id, credit=amount))
        elif amount < 0:
            ledger_lines.append(LedgerLine(account_id, debit=-amount))
    return ledger_lines
