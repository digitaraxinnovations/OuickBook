"""
Inventory valuation reports, built from the stock history (InventoryMovement).

- Summary: quantity on hand, average cost and value of each item on a date.
  The total equals the Inventory Asset account on the Balance Sheet.
- Detail:  every stock movement of each item in a period, with the value
  at the start and at the end.
"""

from datetime import date
from decimal import Decimal

from app.core.money import ZERO, to_money
from app.reports.base import Report
from app.repositories.inventory_repositories import InventoryMovementRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.report import ReportOptions, ReportResult, ReportRow


def quantity_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


class InventoryValuationSummaryReport(Report):
    key = "inventory-valuation-summary"
    group = "Inventory"
    title = "Inventory Valuation Summary"
    description = "Quantity on hand, average cost and value of each inventory item."
    uses_start_date = False

    def __init__(self, product_repository: ProductRepository, movement_repository: InventoryMovementRepository):
        self.product_repository = product_repository
        self.movement_repository = movement_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        totals = self.movement_repository.totals_up_to(company_id, end_date)
        rows = []
        for product in self.product_repository.list_all(company_id):
            if product.id not in totals:
                continue
            quantity, value = totals[product.id]
            if quantity == 0 and value == 0:
                continue
            average = to_money(value / quantity) if quantity != 0 else ZERO
            label = f"{product.name} - {quantity_text(quantity)} on hand at {average:,.2f} average"
            rows.append(ReportRow(label=label, amount=value))

        section = self.make_section("Inventory", rows)
        summary = [ReportRow(label="Total inventory value", amount=section.total)]
        return self.make_result(start_date, end_date, [section], summary)


class InventoryValuationDetailReport(Report):
    key = "inventory-valuation-detail"
    group = "Inventory"
    title = "Inventory Valuation Detail"
    description = "Every purchase, sale and adjustment of each inventory item, with its value."

    def __init__(self, product_repository: ProductRepository, movement_repository: InventoryMovementRepository):
        self.product_repository = product_repository
        self.movement_repository = movement_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        opening = {}
        if start_date is not None:
            day_before = date.fromordinal(start_date.toordinal() - 1)
            opening = self.movement_repository.totals_up_to(company_id, day_before)

        movements_per_product = {}
        for movement in self.movement_repository.between(company_id, start_date, end_date):
            movements_per_product.setdefault(movement.product_id, []).append(movement)

        sections = []
        grand_total = ZERO
        for product in self.product_repository.list_all(company_id):
            movements = movements_per_product.get(product.id, [])
            start_quantity, start_value = opening.get(product.id, (ZERO, ZERO))
            if not movements and start_quantity == 0 and start_value == 0:
                continue

            rows = [ReportRow(label=f"Starting value ({quantity_text(start_quantity)} on hand)", amount=start_value)]
            quantity = start_quantity
            for movement in movements:
                quantity += movement.quantity
                change = quantity_text(movement.quantity)
                if movement.quantity > 0:
                    change = "+" + change
                label = f"{movement.movement_date:%b %d, %Y}  {movement.description}  ({change}, {quantity_text(quantity)} on hand)"
                rows.append(ReportRow(label=label, amount=movement.value))
            section = self.make_section(product.name, rows)
            sections.append(section)
            grand_total += section.total

        summary = [ReportRow(label="Total inventory value at the end of the period", amount=grand_total)]
        return self.make_result(start_date, end_date, sections, summary)
