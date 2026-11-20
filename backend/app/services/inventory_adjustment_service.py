"""
Inventory quantity adjustments (stock counts, damage, theft, found stock).

    Less stock:  Debit the adjustment account, Credit Inventory Asset   (FIFO cost)
    More stock:  Debit Inventory Asset, Credit the adjustment account   (item's purchase cost)

The adjustment account defaults to "Inventory Shrinkage".
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import InventoryAdjustment, InventoryAdjustmentLine
from app.models.enums import JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.inventory_repositories import InventoryAdjustmentRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.inventory import InventoryAdjustmentCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.inventory_service import AccountTotals, InventoryService, StockSource
from app.services.ledger_service import LedgerService
from app.services.numbering import DocumentNumberService
from app.services.system_accounts import SystemAccounts

STOCK_SOURCE = "ADJUSTMENT"


class InventoryAdjustmentService(BaseService):
    def __init__(
        self,
        session,
        repository: InventoryAdjustmentRepository,
        product_repository: ProductRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        system_accounts: SystemAccounts,
        numbering: DocumentNumberService,
        inventory: InventoryService,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.repository = repository
        self.product_repository = product_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.system_accounts = system_accounts
        self.numbering = numbering
        self.inventory = inventory
        self.ledger = ledger

    def list(self, company_id: int) -> list[InventoryAdjustment]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, adjustment_id: int) -> InventoryAdjustment:
        adjustment = self.repository.get(company_id, adjustment_id)
        if adjustment is None:
            raise NotFoundError("Inventory adjustment not found.")
        return adjustment

    def create(self, company_id: int, data: InventoryAdjustmentCreate) -> InventoryAdjustment:
        account = self.adjustment_account(company_id, data.account_id)
        adjustment = InventoryAdjustment(
            company_id=company_id,
            adjustment_number=self.numbering.next_number(company_id, "INVENTORY_ADJUSTMENT"),
            adjustment_date=data.adjustment_date,
            account_id=account.id,
            memo=data.memo,
            is_void=False,
        )
        self.repository.add(adjustment)

        source = StockSource(STOCK_SOURCE, adjustment.id, data.adjustment_date, f"Inventory adjustment {adjustment.adjustment_number}")
        totals = AccountTotals()
        seen = set()
        for line in data.lines:
            if line.quantity_change == 0:
                continue
            product = self.product_repository.get(company_id, line.product_id)
            if product is None or not product.is_inventory:
                raise BusinessRuleError("Only inventory items can be adjusted.")
            if product.id in seen:
                raise BusinessRuleError(f"{product.name} is on the adjustment twice.")
            seen.add(product.id)

            asset_id = self.inventory.asset_account_id(company_id, product)
            if line.quantity_change > 0:
                value = self.inventory.receive(company_id, product, line.quantity_change, product.purchase_cost, source)
                totals.debit(asset_id, value)
                totals.credit(account.id, value)
            else:
                value = -self.inventory.issue(company_id, product, -line.quantity_change, source)
                totals.debit(account.id, -value)
                totals.credit(asset_id, -value)
            adjustment.lines.append(
                InventoryAdjustmentLine(product_id=product.id, quantity_change=line.quantity_change, value_change=value)
            )

        if not adjustment.lines:
            raise BusinessRuleError("Change the quantity of at least one item.")

        ledger_lines = totals.ledger_lines()
        # Items with no cost change the quantity but not the books.
        if ledger_lines:
            entry = self.ledger.post(
                company_id=company_id,
                entry_date=data.adjustment_date,
                source_type=JournalSource.INVENTORY_ADJUST,
                source_id=adjustment.id,
                memo=data.memo or source.description,
                lines=ledger_lines,
            )
            adjustment.journal_entry_id = entry.id
        self.commit()
        return adjustment

    def adjustment_account(self, company_id: int, account_id: int | None):
        if account_id is None:
            return self.system_accounts.get(company_id, SystemAccount.INVENTORY_SHRINKAGE)
        account = self.account_repository.get(company_id, account_id)
        if account is None or not account.is_active:
            raise BusinessRuleError("Choose the account for the adjustment (e.g. Inventory Shrinkage).")
        return account

    def void(self, company_id: int, adjustment_id: int) -> InventoryAdjustment:
        adjustment = self.get(company_id, adjustment_id)
        if adjustment.is_void:
            raise BusinessRuleError("This adjustment is already void.")
        description = f"Void of inventory adjustment {adjustment.adjustment_number}"
        self.inventory.undo(company_id, STOCK_SOURCE, adjustment.id, date.today(), description)
        if adjustment.journal_entry_id is not None:
            original = self.journal_repository.get(company_id, adjustment.journal_entry_id)
            self.ledger.reverse(company_id, original, date.today(), JournalSource.INVENTORY_ADJUST, description)
        adjustment.is_void = True
        self.commit()
        return adjustment
