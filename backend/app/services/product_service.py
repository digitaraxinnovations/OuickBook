"""
Products and services you sell and buy.

Inventory items also get a starting quantity when they are created:
    Debit Inventory Asset, Credit Opening Balance Equity
"""

from decimal import Decimal

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models import BundleComponent, Product
from app.models.enums import AccountType, JournalSource, ProductType
from app.repositories.account_repository import AccountRepository
from app.repositories.inventory_repositories import InventoryMovementRepository, ProductCategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductWrite
from app.seed.default_accounts import SystemAccount
from app.services.base import CrudService
from app.services.inventory_service import InventoryService, StockSource
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts

STOCK_SOURCE = "PRODUCT_START"


class ProductService(CrudService):
    model = Product
    item_name = "Product or service"

    def __init__(
        self,
        session,
        repository: ProductRepository,
        account_repository: AccountRepository,
        category_repository: ProductCategoryRepository,
        movement_repository: InventoryMovementRepository,
        system_accounts: SystemAccounts,
        inventory: InventoryService,
        ledger: LedgerService,
    ):
        super().__init__(session, repository)
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.movement_repository = movement_repository
        self.system_accounts = system_accounts
        self.inventory = inventory
        self.ledger = ledger

    # ---------- create / update ----------

    def create_record(self, company_id: int, data: ProductWrite) -> Product:
        """Also used by the CSV import, which commits once at the end."""
        self.check_name(company_id, data.name, None)
        product = super().create_record(company_id, data)
        if product.is_inventory and data.initial_quantity > 0:
            self.add_starting_stock(company_id, product, data)
        return product

    def update(self, company_id: int, record_id: int, data: ProductWrite) -> Product:
        product = self.get(company_id, record_id)
        self.check_name(company_id, data.name, product.id)
        changing_type = data.product_type != product.product_type
        if changing_type and product.is_inventory and self.movement_repository.has_any(company_id, product.id):
            raise BusinessRuleError("This inventory item has stock history, so its type cannot change. Make it inactive instead.")
        if changing_type and (data.product_type == ProductType.BUNDLE or product.product_type == ProductType.BUNDLE):
            raise BusinessRuleError("A bundle cannot be changed into another type of item, or the other way round.")
        return super().update(company_id, record_id, data)

    def check_name(self, company_id: int, name: str, product_id: int | None) -> None:
        existing = self.repository.get_by_name(company_id, name)
        if existing is not None and existing.id != product_id:
            raise ConflictError(f'A product or service named "{name}" already exists.')

    def add_starting_stock(self, company_id: int, product: Product, data: ProductWrite) -> None:
        if data.as_of_date is None:
            raise BusinessRuleError("Enter the date of the starting quantity (as of date).")
        source = StockSource(STOCK_SOURCE, product.id, data.as_of_date, f"Starting quantity of {product.name}")
        value = self.inventory.receive(company_id, product, data.initial_quantity, data.purchase_cost, source)
        if value <= 0:
            return
        equity = self.system_accounts.get(company_id, SystemAccount.OPENING_BALANCE_EQUITY)
        self.ledger.post(
            company_id=company_id,
            entry_date=data.as_of_date,
            source_type=JournalSource.INVENTORY_START,
            source_id=product.id,
            memo=source.description,
            lines=[
                LedgerLine(self.inventory.asset_account_id(company_id, product), debit=value),
                LedgerLine(equity.id, credit=value),
            ],
        )

    # ---------- rules ----------

    def validate(self, company_id: int, data: ProductWrite) -> None:
        self.check_account(company_id, data.income_account_id, (AccountType.INCOME,), "an income account for sales of this item")
        self.check_account(company_id, data.expense_account_id, (AccountType.EXPENSE,), "an expense account for purchases")
        self.check_account(company_id, data.inventory_asset_account_id, (AccountType.ASSET,), "an asset account for the stock")
        self.check_account(company_id, data.cogs_account_id, (AccountType.EXPENSE,), "an expense account for cost of goods sold")
        if data.category_id is not None and self.category_repository.get(company_id, data.category_id) is None:
            raise BusinessRuleError("That category does not exist.")

        if data.product_type == ProductType.BUNDLE:
            self.check_components(company_id, data)
        elif data.components:
            raise BusinessRuleError("Only bundles have components.")

    def check_account(self, company_id: int, account_id: int | None, types: tuple, what: str) -> None:
        if account_id is None:
            return
        account = self.account_repository.get(company_id, account_id)
        if account is None or account.account_type not in types:
            raise BusinessRuleError(f"Please choose {what}.")

    def check_components(self, company_id: int, data: ProductWrite) -> None:
        if not data.components:
            raise BusinessRuleError("Add at least one item to the bundle.")
        seen = set()
        for component in data.components:
            item = self.repository.get(company_id, component.product_id)
            if item is None:
                raise BusinessRuleError("A bundle item does not exist.")
            if item.product_type == ProductType.BUNDLE:
                raise BusinessRuleError("A bundle cannot contain another bundle.")
            if item.id in seen:
                raise BusinessRuleError(f"{item.name} is in the bundle twice.")
            seen.add(item.id)

    def apply_changes(self, company_id: int, record: Product, data: ProductWrite) -> None:
        record.name = data.name
        record.sku = data.sku
        record.product_type = data.product_type
        record.category_id = data.category_id
        record.description = data.description
        record.sales_price = data.sales_price
        record.is_active = data.is_active
        record.taxable = data.taxable
        record.purchase_description = data.purchase_description
        record.purchase_cost = data.purchase_cost
        record.expense_account_id = data.expense_account_id

        if data.income_account_id is not None:
            record.income_account_id = data.income_account_id
        else:
            sales_account = self.system_accounts.get(company_id, SystemAccount.SALES)
            record.income_account_id = sales_account.id

        if data.product_type == ProductType.INVENTORY:
            record.inventory_asset_account_id = data.inventory_asset_account_id
            record.cogs_account_id = data.cogs_account_id
            record.reorder_point = data.reorder_point
        else:
            record.inventory_asset_account_id = None
            record.cogs_account_id = None
            record.reorder_point = None
        if record.quantity_on_hand is None:
            record.quantity_on_hand = Decimal("0")

        record.components.clear()
        if data.product_type == ProductType.BUNDLE:
            self.session.flush()
            for component in data.components:
                record.components.append(BundleComponent(product_id=component.product_id, quantity=component.quantity))
            # A bundle's price is the sum of its items.
            total = Decimal("0")
            for component in data.components:
                total += self.repository.get(company_id, component.product_id).sales_price * component.quantity
            record.sales_price = total
            record.taxable = data.taxable

