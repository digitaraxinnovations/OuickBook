from app.core.exceptions import BusinessRuleError
from app.models import Product
from app.models.enums import AccountType
from app.repositories.account_repository import AccountRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductWrite
from app.seed.default_accounts import SystemAccount
from app.services.base import CrudService


class ProductService(CrudService):
    """Products and services you sell."""

    model = Product
    item_name = "Product or service"

    def __init__(self, session, repository: ProductRepository, account_repository: AccountRepository):
        super().__init__(session, repository)
        self.account_repository = account_repository

    def validate(self, company_id: int, data: ProductWrite) -> None:
        if data.income_account_id is None:
            return
        account = self.account_repository.get(company_id, data.income_account_id)
        if account is None or account.account_type != AccountType.INCOME:
            raise BusinessRuleError("Please choose an income account for this item.")

    def apply_changes(self, company_id: int, record: Product, data: ProductWrite) -> None:
        record.name = data.name
        record.sku = data.sku
        record.product_type = data.product_type
        record.description = data.description
        record.sales_price = data.sales_price
        record.is_active = data.is_active
        record.taxable = data.taxable

        if data.income_account_id is not None:
            record.income_account_id = data.income_account_id
        else:
            sales_account = self.account_repository.get_by_system_key(company_id, SystemAccount.SALES)
            record.income_account_id = sales_account.id
