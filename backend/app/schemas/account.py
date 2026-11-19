from decimal import Decimal

from pydantic import Field

from app.models.enums import AccountType
from app.schemas.common import CleanStringsModel, ORMModel


class AccountCreate(CleanStringsModel):
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=20)
    account_type: AccountType
    detail_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    parent_id: int | None = None


class AccountUpdate(CleanStringsModel):
    # The account type cannot change after creation - it would rewrite history.
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=20)
    detail_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    parent_id: int | None = None
    is_active: bool = True


class AccountRead(ORMModel):
    id: int
    code: str | None
    name: str
    account_type: AccountType
    detail_type: str
    description: str | None
    system_key: str | None
    is_active: bool
    parent_id: int | None
    # "Parent:Child" style name, filled in by AccountService
    full_name: str = ""
    # How many parents above this account (0 = top level)
    depth: int = 0
    balance: Decimal = Decimal("0.00")
