from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import ProductType
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel


class BundleComponentInput(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class ProductWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str | None = Field(default=None, max_length=100)
    product_type: ProductType = ProductType.SERVICE
    category_id: int | None = None
    description: str | None = None
    sales_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    # When empty, the company's default "Sales" income account is used.
    income_account_id: int | None = None
    is_active: bool = True
    taxable: bool = True

    # Purchasing
    purchase_description: str | None = None
    purchase_cost: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    expense_account_id: int | None = None

    # Inventory items. Empty accounts = Inventory Asset / Cost of Goods Sold.
    inventory_asset_account_id: int | None = None
    cogs_account_id: int | None = None
    reorder_point: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    # Only used when the item is created: stock you already have.
    initial_quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    as_of_date: date | None = None

    # Bundles
    components: list[BundleComponentInput] = Field(default_factory=list)


class CategorySummary(ORMModel):
    id: int
    name: str


class BundleComponentRead(BaseModel):
    product_id: int
    name: str
    quantity: Decimal
    sales_price: Decimal


class ProductRead(ORMModel):
    id: int
    name: str
    sku: str | None
    product_type: ProductType
    category: CategorySummary | None
    description: str | None
    sales_price: Decimal
    income_account: AccountSummary
    is_active: bool
    taxable: bool
    purchase_description: str | None
    purchase_cost: Decimal
    expense_account_id: int | None
    inventory_asset_account_id: int | None
    cogs_account_id: int | None
    quantity_on_hand: Decimal
    reorder_point: Decimal | None
    is_low_stock: bool
    components: list[BundleComponentRead] = Field(default_factory=list)


# ---------- categories and price rules ----------


class CategoryWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None


class CategoryRead(ORMModel):
    id: int
    name: str
    parent_id: int | None


class PriceRuleWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=100)
    adjustment_percent: Decimal = Field(gt=-100, le=1000, max_digits=7, decimal_places=2)
    customer_id: int | None = None
    category_id: int | None = None
    product_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True


class PriceRuleRead(ORMModel):
    id: int
    name: str
    adjustment_percent: Decimal
    customer_id: int | None
    category_id: int | None
    product_id: int | None
    start_date: date | None
    end_date: date | None
    is_active: bool


class ProductPrice(BaseModel):
    product_id: int
    price: Decimal
    rule_name: str | None


# ---------- import / export ----------


class ProductImportRequest(BaseModel):
    # The CSV file's text.
    content: str = Field(min_length=1)


class ProductImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]
