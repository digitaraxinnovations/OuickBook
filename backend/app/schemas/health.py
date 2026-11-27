from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Finding(BaseModel):
    """Something in the books worth a look."""

    # Identifies this exact problem, so "this is fine" can be remembered.
    key: str
    check: str
    severity: Severity
    title: str
    detail: str
    # Page where it can be looked at or fixed.
    link: str
    dismissed: bool = False


class HealthReport(BaseModel):
    score: int
    findings: list[Finding]


class DismissalWrite(BaseModel):
    key: str = Field(min_length=1, max_length=200)
