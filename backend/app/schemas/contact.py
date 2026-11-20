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


class CustomerWrite(ContactWrite):
    # Default payment terms for this customer's invoices.
    terms_id: int | None = None
    tax_exempt: bool = False
    exemption_reason: str | None = Field(default=None, max_length=200)
    default_tax_code_id: int | None = None


class CustomerRead(ContactRead):
    terms_id: int | None
    tax_exempt: bool
    exemption_reason: str | None
    default_tax_code_id: int | None
    # Unpaid invoices minus unused credits.
    open_balance: Decimal = Decimal("0.00")


class VendorWrite(ContactWrite):
    terms_id: int | None = None
    track_1099: bool = False
    tax_id: str | None = Field(default=None, max_length=30)


class VendorRead(ContactRead):
    terms_id: int | None
    track_1099: bool
    tax_id: str | None
    # Unpaid bills minus unused vendor credits.
    open_balance: Decimal = Decimal("0.00")
