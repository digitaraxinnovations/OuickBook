from decimal import Decimal

from pydantic import EmailStr, Field

from app.schemas.common import CleanStringsModel, ORMModel


class ContactWrite(CleanStringsModel):
    """Fields a user fills in for a customer or a vendor."""

    display_name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    is_active: bool = True


class ContactRead(ORMModel):
    id: int
    display_name: str
    company_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    notes: str | None
    is_active: bool


class CustomerRead(ContactRead):
    open_balance: Decimal = Decimal("0.00")


class VendorRead(ContactRead):
    pass
