from app.models import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    model = Product

    def order_by_columns(self) -> list:
        return [Product.name]
