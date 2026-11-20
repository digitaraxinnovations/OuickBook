from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import ProductType
from app.models.inventory import BundleComponent, ProductCategory


class Product(CompanyOwnedMixin, TimestampMixin, Base):
    """
    An item on the "Products and services" list.

    - SERVICE / NON_INVENTORY: sold (and maybe bought) without counting stock.
    - INVENTORY: stock is counted and costed (FIFO); selling it posts cost of goods sold.
    - BUNDLE: a set of other items sold together; it has no stock of its own.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str | None] = mapped_column(String(100))
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType, native_enum=False, length=20))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))
    description: Mapped[str | None] = mapped_column(Text)
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Sales of this item are recorded in this income account.
    income_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Sales tax is charged on this item (unless the customer is exempt).
    taxable: Mapped[bool] = mapped_column(server_default=text("true"))

    # ----- purchasing -----
    purchase_description: Mapped[str | None] = mapped_column(Text)
    # What you usually pay. Also the cost of stock added by an adjustment.
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    # Non-inventory items and services you buy: the expense category.
    expense_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))

    # ----- inventory items only -----
    inventory_asset_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    cogs_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    # Show a "low stock" warning at or below this quantity.
    reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    income_account: Mapped[Account] = relationship(foreign_keys=[income_account_id])
    category: Mapped[ProductCategory | None] = relationship()
    components: Mapped[list[BundleComponent]] = relationship(
        foreign_keys=[BundleComponent.bundle_id],
        cascade="all, delete-orphan",
        order_by=BundleComponent.id,
    )

    @property
    def is_inventory(self) -> bool:
        return self.product_type == ProductType.INVENTORY

    @property
    def is_low_stock(self) -> bool:
        return self.is_inventory and self.reorder_point is not None and self.quantity_on_hand <= self.reorder_point
