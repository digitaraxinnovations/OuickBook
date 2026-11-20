from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    InventoryAdjustment,
    InventoryLayer,
    InventoryMovement,
    InventoryUse,
    PriceRule,
    ProductCategory,
)
from app.repositories.base import BaseRepository


class ProductCategoryRepository(BaseRepository):
    model = ProductCategory

    def order_by_columns(self) -> list:
        return [ProductCategory.name]

    def list_all(self, company_id: int, active_only: bool = False) -> list[ProductCategory]:
        query = select(ProductCategory).where(ProductCategory.company_id == company_id)
        return list(self.session.scalars(query.order_by(ProductCategory.name)))

    def get_by_name(self, company_id: int, name: str) -> ProductCategory | None:
        query = select(ProductCategory).where(
            ProductCategory.company_id == company_id, func.lower(ProductCategory.name) == name.lower()
        )
        return self.session.scalar(query)


class PriceRuleRepository(BaseRepository):
    model = PriceRule

    def order_by_columns(self) -> list:
        return [PriceRule.name]


class InventoryLayerRepository(BaseRepository):
    model = InventoryLayer

    def open_layers(self, company_id: int, product_id: int) -> list[InventoryLayer]:
        """Layers with stock left, oldest first (FIFO)."""
        query = (
            select(InventoryLayer)
            .where(
                InventoryLayer.company_id == company_id,
                InventoryLayer.product_id == product_id,
                InventoryLayer.remaining > 0,
            )
            .order_by(InventoryLayer.layer_date, InventoryLayer.id)
        )
        return list(self.session.scalars(query))

    def for_source(self, company_id: int, source_type: str, source_id: int) -> list[InventoryLayer]:
        query = select(InventoryLayer).where(
            InventoryLayer.company_id == company_id,
            InventoryLayer.source_type == source_type,
            InventoryLayer.source_id == source_id,
        )
        return list(self.session.scalars(query))

    def latest(self, company_id: int, product_id: int) -> InventoryLayer | None:
        query = (
            select(InventoryLayer)
            .where(InventoryLayer.company_id == company_id, InventoryLayer.product_id == product_id)
            .order_by(InventoryLayer.layer_date.desc(), InventoryLayer.id.desc())
        )
        return self.session.scalars(query).first()


class InventoryUseRepository(BaseRepository):
    model = InventoryUse

    def for_source(self, company_id: int, source_type: str, source_id: int) -> list[InventoryUse]:
        query = select(InventoryUse).where(
            InventoryUse.company_id == company_id,
            InventoryUse.source_type == source_type,
            InventoryUse.source_id == source_id,
            InventoryUse.is_returned.is_(False),
        )
        return list(self.session.scalars(query))


class InventoryMovementRepository(BaseRepository):
    model = InventoryMovement

    def for_source(self, company_id: int, source_type: str, source_id: int) -> list[InventoryMovement]:
        query = select(InventoryMovement).where(
            InventoryMovement.company_id == company_id,
            InventoryMovement.source_type == source_type,
            InventoryMovement.source_id == source_id,
        )
        return list(self.session.scalars(query))

    def for_product(self, company_id: int, product_id: int) -> list[InventoryMovement]:
        query = (
            select(InventoryMovement)
            .where(InventoryMovement.company_id == company_id, InventoryMovement.product_id == product_id)
            .order_by(InventoryMovement.movement_date, InventoryMovement.id)
        )
        return list(self.session.scalars(query))

    def between(self, company_id: int, start: date | None, end: date) -> list[InventoryMovement]:
        query = select(InventoryMovement).where(
            InventoryMovement.company_id == company_id, InventoryMovement.movement_date <= end
        )
        if start is not None:
            query = query.where(InventoryMovement.movement_date >= start)
        return list(self.session.scalars(query.order_by(InventoryMovement.movement_date, InventoryMovement.id)))

    def totals_up_to(self, company_id: int, end: date) -> dict[int, tuple[Decimal, Decimal]]:
        """{product_id: (quantity, value)} on a date."""
        query = (
            select(InventoryMovement.product_id, func.sum(InventoryMovement.quantity), func.sum(InventoryMovement.value))
            .where(InventoryMovement.company_id == company_id, InventoryMovement.movement_date <= end)
            .group_by(InventoryMovement.product_id)
        )
        result = {}
        for product_id, quantity, value in self.session.execute(query):
            result[product_id] = (Decimal(quantity), Decimal(value))
        return result

    def has_any(self, company_id: int, product_id: int) -> bool:
        query = select(InventoryMovement.id).where(
            InventoryMovement.company_id == company_id, InventoryMovement.product_id == product_id
        )
        return self.session.scalars(query).first() is not None


class InventoryAdjustmentRepository(BaseRepository):
    model = InventoryAdjustment

    def order_by_columns(self) -> list:
        return [InventoryAdjustment.adjustment_date.desc(), InventoryAdjustment.id.desc()]
