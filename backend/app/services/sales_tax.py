"""
Works out the sales tax on a sales form and keeps a record of it.

How the tax is worked out:
- Only taxable lines are taxed. Shipping is not taxed.
- A discount lowers the taxable amount by its fair share
  (e.g. a 10% discount takes 10% off the taxable lines too).
- Each rate in the tax code is worked out on its own and rounded to the cent,
  so every agency gets exactly what was charged for it.
- Customers marked tax exempt pay no tax.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.models import Customer, SalesTaxLine, TaxCode, TaxRate
from app.repositories.tax_repositories import SalesTaxLineRepository, TaxCodeRepository


class TaxComponentAmount:
    """The tax for one rate of the tax code."""

    def __init__(self, tax_rate: TaxRate, taxable_amount: Decimal, tax_amount: Decimal):
        self.tax_rate = tax_rate
        self.taxable_amount = taxable_amount
        self.tax_amount = tax_amount

    @property
    def liability_account_id(self) -> int:
        return self.tax_rate.agency.liability_account_id


class SalesTaxResult:
    def __init__(self, tax_code: TaxCode | None = None, components: list[TaxComponentAmount] | None = None):
        self.tax_code = tax_code
        self.components = components or []

    @property
    def tax_code_id(self) -> int | None:
        if self.tax_code is None:
            return None
        return self.tax_code.id

    @property
    def total(self) -> Decimal:
        total = ZERO
        for component in self.components:
            total += component.tax_amount
        return total


class SalesTaxCalculator:
    def __init__(self, tax_code_repository: TaxCodeRepository, tax_line_repository: SalesTaxLineRepository):
        self.tax_code_repository = tax_code_repository
        self.tax_line_repository = tax_line_repository

    def find_code(self, company_id: int, tax_code_id: int | None) -> TaxCode | None:
        if tax_code_id is None:
            return None
        tax_code = self.tax_code_repository.get(company_id, tax_code_id)
        if tax_code is None or not tax_code.is_active:
            raise BusinessRuleError("Please choose an active sales tax rate.")
        return tax_code

    def calculate(self, company_id: int, customer: Customer, tax_code_id: int | None, lines: list, totals) -> SalesTaxResult:
        """`lines` are SalesLineValues or database lines; `totals` is a SalesTotals."""
        tax_code = self.find_code(company_id, tax_code_id)
        if tax_code is None:
            return SalesTaxResult()
        if customer.tax_exempt:
            return SalesTaxResult(tax_code)

        base = self.taxable_base(lines, totals)
        components = []
        for code_rate in tax_code.components:
            tax_rate = code_rate.tax_rate
            tax_amount = to_money(base * tax_rate.rate / Decimal("100"))
            components.append(TaxComponentAmount(tax_rate, base, tax_amount))
        return SalesTaxResult(tax_code, components)

    def taxable_base(self, lines: list, totals) -> Decimal:
        taxable_subtotal = ZERO
        for line in lines:
            if line.taxable:
                taxable_subtotal += line.amount
        if taxable_subtotal <= 0:
            return ZERO

        discount_share = ZERO
        if totals.discount_amount > 0 and totals.subtotal > 0:
            discount_share = to_money(totals.discount_amount * taxable_subtotal / totals.subtotal)
        return taxable_subtotal - discount_share

    # ---------- the tax record behind the liability report ----------

    def record(
        self,
        company_id: int,
        source_type: str,
        source_id: int,
        tax_date: date,
        result: SalesTaxResult,
        is_return: bool,
    ) -> None:
        sign = Decimal("-1") if is_return else Decimal("1")
        for component in result.components:
            self.tax_line_repository.add(
                SalesTaxLine(
                    company_id=company_id,
                    source_type=source_type,
                    source_id=source_id,
                    tax_date=tax_date,
                    agency_id=component.tax_rate.agency_id,
                    tax_rate_id=component.tax_rate.id,
                    taxable_amount=component.taxable_amount * sign,
                    tax_amount=component.tax_amount * sign,
                    is_void=False,
                )
            )

    def void(self, company_id: int, source_type: str, source_id: int) -> None:
        self.tax_line_repository.mark_void(company_id, source_type, source_id)
