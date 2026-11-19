"""
Finds the accounts the app uses automatically (Accounts Receivable, Sales,
Discounts Given...).

Companies created before a new system account existed will not have it,
so a missing one is created on the spot from the default chart of accounts.
"""

from app.models import Account
from app.repositories.account_repository import AccountRepository
from app.seed.default_accounts import DEFAULT_ACCOUNTS


def find_template(system_key: str) -> dict:
    for template in DEFAULT_ACCOUNTS:
        if template["key"] == system_key:
            return template
    raise ValueError(f"No default account has the system key '{system_key}'.")


class SystemAccounts:
    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    def get(self, company_id: int, system_key: str) -> Account:
        account = self.account_repository.get_by_system_key(company_id, system_key)
        if account is not None:
            return account

        template = find_template(system_key)

        # The user may already have an account with that name - reuse it if the type matches.
        existing = self.account_repository.get_by_name(company_id, template["name"])
        if existing is not None and existing.account_type == template["type"] and existing.system_key is None:
            existing.system_key = system_key
            return existing

        name = template["name"]
        if existing is not None:
            name = name + " (system)"
        account = Account(
            company_id=company_id,
            code=template["code"],
            name=name,
            account_type=template["type"],
            detail_type=template["detail"],
            system_key=system_key,
        )
        return self.account_repository.add(account)
