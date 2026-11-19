from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_company_service, get_current_user
from app.models import User
from app.schemas.auth import CompanyRead, CompanyUpdate, LoginRequest, MeResponse, SignupRequest, TokenResponse
from app.services.auth_service import AuthService
from app.services.company_service import CompanyService

router = APIRouter(tags=["Auth & Company"])


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, service: AuthService = Depends(get_auth_service)):
    token = service.signup(data)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    token = service.login(data)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(user=user, company=user.company)


@router.put("/company", response_model=CompanyRead)
def update_company(
    data: CompanyUpdate,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return service.update(user.company_id, data)
