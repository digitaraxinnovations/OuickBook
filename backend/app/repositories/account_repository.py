from sqlalchemy import case, select

from app.models import Account
from app.repositories.base import BaseRepository

# Standard accounting order for the Chart of Accounts and reports.
ACCOUNT_TYPE_ORDER = {
    "ASSET": 1,
    "LIABILITY": 2,
    "EQUITY": 3,
    "INCOME": 4,
    "EXPENSE": 5,
}


class AccountRepository(BaseRepository):
    model = Account

    def order_by_columns(self) -> list:
        type_order = case(ACCOUNT_TYPE_ORDER, value=Account.account_type, else_=9)
        return [type_order, Account.code, Account.name]

    def get_by_system_key(self, company_id: int, system_key: str) -> Account | None:
        query = select(Account).where(
            Account.company_id == company_id,
            Account.system_key == system_key,
        )
        return self.session.scalar(query)

    def get_by_name(self, company_id: int, name: str) -> Account | None:
        query = select(Account).where(
            Account.company_id == company_id,
            Account.name == name,
        )
        return self.session.scalar(query)
