from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import CleanStringsModel, ORMModel


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    company_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    # bcrypt only uses the first 72 bytes of a password
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(ORMModel):
    id: int
    email: str
    full_name: str
    company_id: int


class CompanyRead(ORMModel):
    id: int
    name: str
    currency: str
    email: str | None
    phone: str | None
    address: str | None
    payment_terms_days: int


class CompanyUpdate(CleanStringsModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    payment_terms_days: int = Field(ge=0, le=365)


class MeResponse(BaseModel):
    user: UserRead
    company: CompanyRead
