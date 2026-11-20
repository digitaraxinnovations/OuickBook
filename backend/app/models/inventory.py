"""
Inventory, product categories, bundles and price rules.

How stock is costed (FIFO - first in, first out):
- Every time stock comes in (a bill, an expense, an adjustment, the starting
  quantity) an InventoryLayer is added: "10 units at 4.00 each".
- When stock goes out (a sale, a vendor credit, an adjustment) the oldest
  layers are used first. Each use is saved as an InventoryUse so it can be
  put back if the sale is voided.
- InventoryMovement is the history: one row per product per transaction with
  the quantity and value in or out. The valuation reports add these up, and
  their total always equals the Inventory Asset account balance.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account


class ProductCategory(CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_product_category_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Categories can be nested one inside another.
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))


class BundleComponent(Base):
    """One item inside a bundle (e.g. "2 x Shrub" inside "Hedge kit")."""

    __tablename__ = "bundle_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    product: Mapped["Product"] = relationship(foreign_keys=[product_id])  # noqa: F821

    @property
    def name(self) -> str:
        return self.product.name

    @property
    def sales_price(self) -> Decimal:
        return self.product.sales_price


class PriceRule(CompanyOwnedMixin, TimestampMixin, Base):
    """
    Raise or lower prices by a percentage, for everyone or one customer,
    for all items, one category or one item, between two dates.
    """

    __tablename__ = "price_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # e.g. -10 = 10% off, 5 = 5% more
    adjustment_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)


class InventoryLayer(CompanyOwnedMixin, Base):
    """A batch of stock that came in at one unit cost."""

    __tablename__ = "inventory_layers"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    # Which transaction brought it in, e.g. ("BILL", 12)
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(index=True)
    layer_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    remaining: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4))


class InventoryUse(CompanyOwnedMixin, Base):
    """Part of a layer used up by one transaction."""

    __tablename__ = "inventory_uses"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    layer_id: Mapped[int] = mapped_column(ForeignKey("inventory_layers.id"))
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    # Set when the transaction is voided and the stock is put back.
    is_returned: Mapped[bool] = mapped_column(default=False)

    layer: Mapped[InventoryLayer] = relationship()


class InventoryMovement(CompanyOwnedMixin, Base):
    """Quantity and value in (+) or out (-) of one product, for one transaction."""

    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    movement_date: Mapped[date] = mapped_column(Date, index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int]
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class InventoryAdjustment(CompanyOwnedMixin, TimestampMixin, Base):
    """
    Changes the quantity on hand without a sale or purchase (counts, damage, theft).
        Less stock:  Debit the adjustment account (e.g. Inventory Shrinkage), Credit Inventory Asset
        More stock:  Debit Inventory Asset, Credit the adjustment account
    """

    __tablename__ = "inventory_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    adjustment_number: Mapped[str] = mapped_column(String(20))
    adjustment_date: Mapped[date] = mapped_column(Date)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    memo: Mapped[str | None] = mapped_column(Text)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    is_void: Mapped[bool] = mapped_column(default=False)

    account: Mapped[Account] = relationship()
    lines: Mapped[list["InventoryAdjustmentLine"]] = relationship(
        back_populates="adjustment",
        cascade="all, delete-orphan",
        order_by="InventoryAdjustmentLine.id",
    )


class InventoryAdjustmentLine(Base):
    __tablename__ = "inventory_adjustment_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    adjustment_id: Mapped[int] = mapped_column(ForeignKey("inventory_adjustments.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # Positive adds stock, negative removes it.
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Cost of the whole line (worked out with FIFO for decreases).
    value_change: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    adjustment: Mapped[InventoryAdjustment] = relationship(back_populates="lines")
