from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import AccountSummary, CleanStringsModel, ORMModel


class AdjustmentLineInput(BaseModel):
    product_id: int
    # Positive adds stock, negative removes it.
    quantity_change: Decimal = Field(max_digits=12, decimal_places=2)


class InventoryAdjustmentCreate(CleanStringsModel):
    adjustment_date: date
    # Empty = Inventory Shrinkage.
    account_id: int | None = None
    memo: str | None = Field(default=None, max_length=1000)
    lines: list[AdjustmentLineInput] = Field(min_length=1)


class AdjustmentLineRead(ORMModel):
    product_id: int
    quantity_change: Decimal
    value_change: Decimal


class InventoryAdjustmentRead(ORMModel):
    id: int
    adjustment_number: str
    adjustment_date: date
    account: AccountSummary
    memo: str | None
    is_void: bool
    lines: list[AdjustmentLineRead]


class StockMovementRead(ORMModel):
    id: int
    movement_date: date
    source_type: str
    source_id: int
    description: str
    quantity: Decimal
    value: Decimal
