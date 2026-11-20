from sqlalchemy import func, select

from app.models import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    model = Product

    def order_by_columns(self) -> list:
        return [Product.name]

    def get_by_name(self, company_id: int, name: str) -> Product | None:
        query = select(Product).where(Product.company_id == company_id, func.lower(Product.name) == name.lower())
        return self.session.scalar(query)
