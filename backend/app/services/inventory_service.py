"""
The stock engine: quantity on hand and FIFO cost for inventory items.

Other services call it when stock moves:
- receive()   stock comes in (bill, expense, adjustment, starting quantity, customer return)
- issue()     stock goes out (sale, vendor credit, adjustment) - returns its FIFO cost
- undo()      a transaction is voided - stock goes back to how it was

It never posts journal entries itself and never commits; the calling service
puts the amounts it returns into its own journal entry, so the Inventory
Asset account always matches the stock records.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO, to_money
from app.models import InventoryLayer, InventoryMovement, InventoryUse, Product
from app.repositories.inventory_repositories import (
    InventoryLayerRepository,
    InventoryMovementRepository,
    InventoryUseRepository,
)
from app.repositories.product_repository import ProductRepository
from app.seed.default_accounts import SystemAccount
from app.services.ledger_service import LedgerLine
from app.services.system_accounts import SystemAccounts


class StockSource:
    """The transaction that moves stock, e.g. StockSource("INVOICE", 12, date, "Invoice 1003")."""

    def __init__(self, source_type: str, source_id: int, when: date, description: str):
        self.source_type = source_type
        self.source_id = source_id
        self.when = when
        self.description = description[:200]


class AccountTotals:
    """Adds up debits and credits per account, then turns them into ledger lines."""

    def __init__(self):
        self.amounts = {}

    def debit(self, account_id: int, amount: Decimal) -> None:
        self.amounts[account_id] = self.amounts.get(account_id, ZERO) + amount

    def credit(self, account_id: int, amount: Decimal) -> None:
        self.amounts[account_id] = self.amounts.get(account_id, ZERO) - amount

    def ledger_lines(self) -> list[LedgerLine]:
        lines = []
        for account_id, amount in self.amounts.items():
            if amount > 0:
                lines.append(LedgerLine(account_id, debit=amount))
            elif amount < 0:
                lines.append(LedgerLine(account_id, credit=-amount))
        return lines


class InventoryService:
    def __init__(
        self,
        product_repository: ProductRepository,
        layer_repository: InventoryLayerRepository,
        use_repository: InventoryUseRepository,
        movement_repository: InventoryMovementRepository,
        system_accounts: SystemAccounts,
    ):
        self.product_repository = product_repository
        self.layer_repository = layer_repository
        self.use_repository = use_repository
        self.movement_repository = movement_repository
        self.system_accounts = system_accounts

    # ---------- accounts ----------

    def asset_account_id(self, company_id: int, product: Product) -> int:
        if product.inventory_asset_account_id is not None:
            return product.inventory_asset_account_id
        return self.system_accounts.get(company_id, SystemAccount.INVENTORY_ASSET).id

    def cogs_account_id(self, company_id: int, product: Product) -> int:
        if product.cogs_account_id is not None:
            return product.cogs_account_id
        return self.system_accounts.get(company_id, SystemAccount.COST_OF_GOODS_SOLD).id

    def purchase_line_account(self, company_id: int, product_id: int | None, account_id: int | None) -> tuple[int, Product | None]:
        """
        The account a purchase line is posted to, and its product.
        - Inventory item: its Inventory Asset account.
        - Other item: the category typed, else the item's expense account.
        - No item: the category typed.
        """
        if product_id is None:
            if account_id is None:
                raise BusinessRuleError("Choose a category or a product for every line.")
            return account_id, None

        product = self.product_repository.get(company_id, product_id)
        if product is None:
            raise BusinessRuleError("That product does not exist.")
        if product.product_type.value == "BUNDLE":
            raise BusinessRuleError("Bundles cannot be bought - add their items instead.")
        if product.is_inventory:
            return self.asset_account_id(company_id, product), product
        if account_id is not None:
            return account_id, product
        if product.expense_account_id is not None:
            return product.expense_account_id, product
        raise BusinessRuleError(f"Choose a category for {product.name} (or set its expense account).")

    # ---------- moving stock ----------

    def receive(self, company_id: int, product: Product, quantity: Decimal, unit_cost: Decimal, source: StockSource) -> Decimal:
        """Add stock. Returns its value."""
        if quantity <= 0:
            raise BusinessRuleError("The quantity received must be more than zero.")
        value = to_money(quantity * unit_cost)
        self.layer_repository.add(
            InventoryLayer(
                company_id=company_id,
                product_id=product.id,
                source_type=source.source_type,
                source_id=source.source_id,
                layer_date=source.when,
                quantity=quantity,
                remaining=quantity,
                unit_cost=unit_cost,
            )
        )
        self.add_movement(company_id, product, source, quantity, value)
        return value

    def issue(self, company_id: int, product: Product, quantity: Decimal, source: StockSource) -> Decimal:
        """Take stock out, oldest layers first. Returns its FIFO cost."""
        if quantity <= 0:
            raise BusinessRuleError("The quantity must be more than zero.")
        if quantity > product.quantity_on_hand:
            on_hand = format(product.quantity_on_hand.normalize(), "f")
            raise BusinessRuleError(f"Only {on_hand} of {product.name} on hand - not enough for this transaction.")

        still_needed = quantity
        exact_cost = Decimal("0")
        for layer in self.layer_repository.open_layers(company_id, product.id):
            if still_needed <= 0:
                break
            taken = min(layer.remaining, still_needed)
            layer.remaining = layer.remaining - taken
            still_needed = still_needed - taken
            exact_cost += taken * layer.unit_cost
            self.use_repository.add(
                InventoryUse(
                    company_id=company_id,
                    product_id=product.id,
                    layer_id=layer.id,
                    source_type=source.source_type,
                    source_id=source.source_id,
                    quantity=taken,
                    unit_cost=layer.unit_cost,
                    is_returned=False,
                )
            )
        if still_needed > 0:
            raise BusinessRuleError(f"The stock records for {product.name} are short by {still_needed}.")

        cost = to_money(exact_cost)
        self.add_movement(company_id, product, source, -quantity, -cost)
        return cost

    def current_unit_cost(self, company_id: int, product: Product) -> Decimal:
        """Cost used for stock coming back from a customer: the latest purchase cost."""
        latest = self.layer_repository.latest(company_id, product.id)
        if latest is not None:
            return latest.unit_cost
        return product.purchase_cost

    def undo(self, company_id: int, source_type: str, source_id: int, when: date, description: str) -> None:
        """Put stock back the way it was before a transaction (used when it is voided)."""
        layers = self.layer_repository.for_source(company_id, source_type, source_id)
        for layer in layers:
            if layer.remaining != layer.quantity:
                product = self.product_repository.get(company_id, layer.product_id)
                raise BusinessRuleError(f"Some of the {product.name} from this transaction has already been sold or used.")

        for layer in layers:
            layer.remaining = ZERO
        for use in self.use_repository.for_source(company_id, source_type, source_id):
            use.layer.remaining = use.layer.remaining + use.quantity
            use.is_returned = True

        undo_source = StockSource(source_type, source_id, when, description)
        for movement in self.movement_repository.for_source(company_id, source_type, source_id):
            product = self.product_repository.get(company_id, movement.product_id)
            self.add_movement(company_id, product, undo_source, -movement.quantity, -movement.value)

    def add_movement(self, company_id: int, product: Product, source: StockSource, quantity: Decimal, value: Decimal) -> None:
        self.movement_repository.add(
            InventoryMovement(
                company_id=company_id,
                product_id=product.id,
                movement_date=source.when,
                source_type=source.source_type,
                source_id=source.source_id,
                description=source.description,
                quantity=quantity,
                value=value,
            )
        )
        product.quantity_on_hand = product.quantity_on_hand + quantity

    # ---------- what sales and purchases call ----------

    def cost_of_sales_lines(self, company_id: int, lines: list, source: StockSource, is_return: bool) -> list[LedgerLine]:
        """
        Cost of goods sold for the inventory lines of a sales form.

            Sale:    Debit Cost of Goods Sold, Credit Inventory Asset (FIFO cost)
            Return:  Debit Inventory Asset, Credit Cost of Goods Sold (latest cost)

        A line with a negative amount (e.g. a delayed credit added to an invoice)
        is treated as a return.
        """
        totals = AccountTotals()
        for line in lines:
            if line.product_id is None:
                continue
            product = self.product_repository.get(company_id, line.product_id)
            if not product.is_inventory:
                continue
            asset_id = self.asset_account_id(company_id, product)
            cogs_id = self.cogs_account_id(company_id, product)
            returned = is_return != (line.amount < 0)
            if returned:
                value = self.receive(company_id, product, line.quantity, self.current_unit_cost(company_id, product), source)
                totals.debit(asset_id, value)
                totals.credit(cogs_id, value)
            else:
                cost = self.issue(company_id, product, line.quantity, source)
                totals.debit(cogs_id, cost)
                totals.credit(asset_id, cost)
        return totals.ledger_lines()

    def purchase_lines(self, company_id: int, lines: list, source: StockSource, is_return: bool) -> list[LedgerLine]:
        """
        Stock for the inventory lines of a bill, expense or vendor credit.

        The form already posts each line to the item's Inventory Asset account
        at the price paid. A purchase adds a layer at that price. A return to
        the vendor takes stock out at FIFO cost; any difference between that
        cost and the credit goes to Cost of Goods Sold.
        """
        totals = AccountTotals()
        for line in lines:
            if line.product_id is None:
                continue
            product = self.product_repository.get(company_id, line.product_id)
            if not product.is_inventory:
                continue
            if not is_return:
                unit_cost = line.amount / line.quantity
                self.receive(company_id, product, line.quantity, unit_cost, source)
                continue
            cost = self.issue(company_id, product, line.quantity, source)
            difference = cost - line.amount
            if difference != 0:
                # The credit already took line.amount off Inventory; take off the rest.
                totals.debit(self.cogs_account_id(company_id, product), difference)
                totals.credit(self.asset_account_id(company_id, product), difference)
        return totals.ledger_lines()
