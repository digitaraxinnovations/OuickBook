from datetime import date

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.money import ZERO
from app.models import Account
from app.models.enums import AccountType
from app.repositories.account_repository import AccountRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.base import BaseService

# Same limit QuickBooks uses: a parent plus up to 5 levels of sub-accounts.
MAX_SUB_ACCOUNT_DEPTH = 5


class AccountService(BaseService):
    """Chart of Accounts, including sub-accounts."""

    def __init__(self, session, account_repository: AccountRepository, journal_repository: JournalRepository):
        super().__init__(session)
        self.account_repository = account_repository
        self.journal_repository = journal_repository

    # ---------- reading ----------

    def list_with_balances(self, company_id: int, active_only: bool = False) -> list[Account]:
        """Accounts in tree order (each parent followed by its sub-accounts), with balances."""
        accounts = self.account_repository.list_all(company_id, active_only)

        balances = {}
        for totals in self.journal_repository.totals_by_account(company_id, None, date.max):
            balances[totals.account.id] = totals.balance

        children_by_parent = {}
        top_level = []
        known_ids = set()
        for account in accounts:
            known_ids.add(account.id)
        for account in accounts:
            # `balance`, `full_name` and `depth` are not database columns - they are added for the response.
            account.balance = balances.get(account.id, ZERO)
            if account.parent_id is None or account.parent_id not in known_ids:
                top_level.append(account)
            else:
                children_by_parent.setdefault(account.parent_id, []).append(account)

        ordered = []
        for account in top_level:
            self.add_with_children(account, "", 0, children_by_parent, ordered)
        return ordered

    def add_with_children(self, account: Account, parent_name: str, depth: int, children_by_parent: dict, ordered: list) -> None:
        if parent_name:
            account.full_name = parent_name + ":" + account.name
        else:
            account.full_name = account.name
        account.depth = depth
        ordered.append(account)
        for child in children_by_parent.get(account.id, []):
            self.add_with_children(child, account.full_name, depth + 1, children_by_parent, ordered)

    def get(self, company_id: int, account_id: int) -> Account:
        account = self.account_repository.get(company_id, account_id)
        if account is None:
            raise NotFoundError("Account not found.")
        return account

    # ---------- writing ----------

    def create(self, company_id: int, data: AccountCreate) -> Account:
        self.check_name_is_free(company_id, data.name)
        self.check_parent(company_id, None, data.parent_id, data.account_type)
        account = Account(
            company_id=company_id,
            name=data.name,
            code=data.code,
            account_type=data.account_type,
            detail_type=data.detail_type,
            description=data.description,
            parent_id=data.parent_id,
        )
        self.account_repository.add(account)
        self.commit()
        return account

    def update(self, company_id: int, account_id: int, data: AccountUpdate) -> Account:
        account = self.get(company_id, account_id)
        if data.name != account.name:
            self.check_name_is_free(company_id, data.name)
        if account.system_key and not data.is_active:
            raise BusinessRuleError(f'"{account.name}" is used by the system and cannot be made inactive.')
        self.check_parent(company_id, account.id, data.parent_id, account.account_type)

        account.name = data.name
        account.code = data.code
        account.detail_type = data.detail_type
        account.description = data.description
        account.parent_id = data.parent_id
        account.is_active = data.is_active
        self.commit()
        return account

    # ---------- rules ----------

    def check_name_is_free(self, company_id: int, name: str) -> None:
        if self.account_repository.get_by_name(company_id, name) is not None:
            raise ConflictError(f'An account named "{name}" already exists.')

    def check_parent(self, company_id: int, account_id: int | None, parent_id: int | None, account_type: AccountType) -> None:
        """A parent must exist, have the same type, and must not create a loop."""
        if parent_id is None:
            return
        if parent_id == account_id:
            raise BusinessRuleError("An account cannot be a sub-account of itself.")

        parent = self.account_repository.get(company_id, parent_id)
        if parent is None:
            raise BusinessRuleError("The parent account does not exist.")
        if parent.account_type != account_type:
            raise BusinessRuleError("A sub-account must have the same account type as its parent.")

        # Walk up from the parent. If we meet this account, the change would create a loop.
        depth = 1
        current = parent
        while current.parent_id is not None:
            if current.parent_id == account_id:
                raise BusinessRuleError("This change would make an account a sub-account of its own sub-account.")
            depth += 1
            if depth > MAX_SUB_ACCOUNT_DEPTH:
                raise BusinessRuleError(f"Sub-accounts can only be {MAX_SUB_ACCOUNT_DEPTH} levels deep.")
            current = self.account_repository.get(company_id, current.parent_id)
