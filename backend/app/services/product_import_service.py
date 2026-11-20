"""
Products and services to and from a CSV file (Excel can open and save it).

Columns (a header row is required; only Name is required):
    Name, SKU, Type, Description, Sales price, Purchase cost, Taxable,
    Category, Quantity on hand, Reorder point, Active

Importing adds new items and updates items with the same name. The quantity
on hand of a new inventory item becomes its starting quantity (as of today);
the quantity of an existing item is never changed by an import - use an
inventory adjustment for that.
"""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from app.core.exceptions import AppError
from app.models import Product
from app.models.enums import ProductType
from app.repositories.inventory_repositories import ProductCategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import CategoryWrite, ProductImportResult, ProductWrite
from app.services.base import BaseService
from app.services.catalog_service import CatalogService
from app.services.product_service import ProductService

COLUMNS = [
    "Name",
    "SKU",
    "Type",
    "Description",
    "Sales price",
    "Purchase cost",
    "Taxable",
    "Category",
    "Quantity on hand",
    "Reorder point",
    "Active",
]

TYPE_NAMES = {
    "service": ProductType.SERVICE,
    "non-inventory": ProductType.NON_INVENTORY,
    "non_inventory": ProductType.NON_INVENTORY,
    "inventory": ProductType.INVENTORY,
}


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def read_bool(text: str, default: bool) -> bool:
    if not text:
        return default
    return text.strip().lower() in ("yes", "y", "true", "1")


def read_number(text: str, column: str) -> Decimal | None:
    if not text or not text.strip():
        return None
    try:
        return Decimal(text.replace(",", "").replace("$", "").strip())
    except InvalidOperation:
        raise ValueError(f'"{text}" in {column} is not a number')


class ProductImportService(BaseService):
    def __init__(
        self,
        session,
        product_repository: ProductRepository,
        category_repository: ProductCategoryRepository,
        product_service: ProductService,
        catalog_service: CatalogService,
    ):
        super().__init__(session)
        self.product_repository = product_repository
        self.category_repository = category_repository
        self.product_service = product_service
        self.catalog_service = catalog_service

    # ---------- export ----------

    def export_csv(self, company_id: int) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(COLUMNS)
        for product in self.product_repository.list_all(company_id):
            if product.product_type == ProductType.BUNDLE:
                continue
            writer.writerow(
                [
                    product.name,
                    product.sku or "",
                    product.product_type.value.replace("_", "-").title(),
                    product.description or "",
                    product.sales_price,
                    product.purchase_cost,
                    yes_no(product.taxable),
                    product.category.name if product.category else "",
                    product.quantity_on_hand if product.is_inventory else "",
                    product.reorder_point if product.reorder_point is not None else "",
                    yes_no(product.is_active),
                ]
            )
        return output.getvalue()

    # ---------- import ----------

    def import_csv(self, company_id: int, content: str) -> ProductImportResult:
        reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
        created = 0
        updated = 0
        errors = []
        for row_number, row in enumerate(reader, start=2):
            clean_row = {}
            for key, value in row.items():
                if key is not None:
                    clean_row[key.strip().lower()] = (value or "").strip()
            name = clean_row.get("name", "")
            if not name:
                errors.append(f"Row {row_number}: the name is empty.")
                continue
            try:
                existing = self.product_repository.get_by_name(company_id, name)
                data = self.row_to_product(company_id, clean_row, existing)
                if existing is None:
                    self.product_service.create_record(company_id, data)
                    created += 1
                else:
                    self.product_service.validate(company_id, data)
                    self.product_service.apply_changes(company_id, existing, data)
                    updated += 1
                self.session.flush()
            except (AppError, ValueError) as problem:
                errors.append(f"Row {row_number} ({name}): {problem}")

        if errors:
            # All or nothing, so a half-imported file never needs cleaning up.
            self.session.rollback()
            return ProductImportResult(created=0, updated=0, errors=errors)
        self.commit()
        return ProductImportResult(created=created, updated=updated, errors=[])

    def row_to_product(self, company_id: int, row: dict, existing: Product | None) -> ProductWrite:
        type_text = row.get("type", "").lower()
        if type_text:
            if type_text not in TYPE_NAMES:
                raise ValueError(f'unknown type "{row.get("type")}" (use Service, Non-inventory or Inventory)')
            product_type = TYPE_NAMES[type_text]
        elif existing is not None:
            product_type = existing.product_type
        else:
            product_type = ProductType.SERVICE

        category_id = None
        category_name = row.get("category", "")
        if category_name:
            category = self.category_repository.get_by_name(company_id, category_name)
            if category is None:
                category = self.catalog_service.save_category_without_commit(company_id, CategoryWrite(name=category_name))
            category_id = category.id
        elif existing is not None:
            category_id = existing.category_id

        quantity = read_number(row.get("quantity on hand", ""), "Quantity on hand") or Decimal("0")
        return ProductWrite(
            name=row["name"],
            sku=row.get("sku") or (existing.sku if existing else None),
            product_type=product_type,
            category_id=category_id,
            description=row.get("description") or (existing.description if existing else None),
            sales_price=read_number(row.get("sales price", ""), "Sales price") or Decimal("0"),
            purchase_cost=read_number(row.get("purchase cost", ""), "Purchase cost") or Decimal("0"),
            taxable=read_bool(row.get("taxable", ""), True),
            is_active=read_bool(row.get("active", ""), True),
            reorder_point=read_number(row.get("reorder point", ""), "Reorder point"),
            income_account_id=existing.income_account_id if existing else None,
            expense_account_id=existing.expense_account_id if existing else None,
            inventory_asset_account_id=existing.inventory_asset_account_id if existing else None,
            cogs_account_id=existing.cogs_account_id if existing else None,
            initial_quantity=quantity if existing is None else Decimal("0"),
            as_of_date=date.today(),
        )
