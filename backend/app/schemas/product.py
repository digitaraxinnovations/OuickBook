from decimal import Decimal

from pydantic import Field

from app.models.enums import ProductType
from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel


class ProductWrite(CleanStringsModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str | None = Field(default=None, max_length=100)
    product_type: ProductType = ProductType.SERVICE
    description: str | None = None
    sales_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    # When empty, the company's default "Sales" income account is used.
    income_account_id: int | None = None
    is_active: bool = True
    taxable: bool = True


class ProductRead(ORMModel):
    id: int
    name: str
    sku: str | None
    product_type: ProductType
    description: str | None
    sales_price: Decimal
    income_account: AccountSummary
    is_active: bool
    taxable: bool
