"""
Building blocks shared by many schemas.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import AccountType


class ORMModel(BaseModel):
    """Base for response schemas that are filled from database objects."""

    model_config = ConfigDict(from_attributes=True)


class CleanStringsModel(BaseModel):
    """
    Base for request schemas.
    Turns empty strings ("") into None, so an empty optional form field
    is treated as "not given" instead of failing validation.
    """

    @field_validator("*", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class AccountSummary(ORMModel):
    id: int
    name: str
    account_type: AccountType


class ContactSummary(ORMModel):
    id: int
    display_name: str
    email: str | None = None


class MessageResponse(BaseModel):
    message: str
