from app.models import Customer, Vendor
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository):
    model = Customer

    def order_by_columns(self) -> list:
        return [Customer.display_name]


class VendorRepository(BaseRepository):
    model = Vendor

    def order_by_columns(self) -> list:
        return [Vendor.display_name]
