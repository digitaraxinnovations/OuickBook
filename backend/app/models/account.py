from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin
from app.models.enums import AccountType


class Account(CompanyOwnedMixin, TimestampMixin, Base):
    """One line in the Chart of Accounts (for example "Checking" or "Rent")."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_account_company_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(150))
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType, native_enum=False, length=20))
    detail_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    # Accounts the app needs to find automatically (e.g. "accounts_receivable").
    # Users cannot delete or deactivate these.
    system_key: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Set when this is a sub-account (e.g. "Electric" under "Utilities").
    # A sub-account always has the same account type as its parent.
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
