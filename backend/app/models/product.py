from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.account import Account
from app.models.enums import ProductType


class Product(CompanyOwnedMixin, TimestampMixin, Base):
    """An item on the "Products and services" list."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str | None] = mapped_column(String(100))
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType, native_enum=False, length=20))
    description: Mapped[str | None] = mapped_column(Text)
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Sales of this item are recorded in this income account.
    income_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    income_account: Mapped[Account] = relationship()
