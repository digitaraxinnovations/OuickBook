from decimal import Decimal

from pydantic import Field, field_validator

from app.models.enums import AccountType
from app.schemas.common import CleanStringsModel, ORMModel
from app.seed.default_accounts import FORM_1099_BOXES, TAX_LINES


class AccountWriteBase(CleanStringsModel):
    """Fields shared by create and update."""

    box_1099: str | None = None
    tax_line: str | None = None

    @field_validator("tax_line")
    @classmethod
    def check_tax_line(cls, value: str | None) -> str | None:
        if value is not None and value not in TAX_LINES:
            raise ValueError("Unknown tax category.")
        return value

    @field_validator("box_1099")
    @classmethod
    def check_box_1099(cls, value: str | None) -> str | None:
        if value is not None and value not in FORM_1099_BOXES:
            raise ValueError("Unknown 1099 box.")
        return value


class AccountCreate(AccountWriteBase):
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=20)
    account_type: AccountType
    detail_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    parent_id: int | None = None


class AccountUpdate(AccountWriteBase):
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
    box_1099: str | None
    tax_line: str | None
    # "Parent:Child" style name, filled in by AccountService
    full_name: str = ""
    # How many parents above this account (0 = top level)
    depth: int = 0
    balance: Decimal = Decimal("0.00")
