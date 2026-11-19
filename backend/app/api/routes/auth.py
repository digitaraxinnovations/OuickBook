from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_company_service, get_current_user
from app.models import User
from app.schemas.auth import CompanyRead, CompanyUpdate, LoginRequest, MeResponse, SignupRequest, TokenResponse
from app.schemas.sales_extras import LogoRead, LogoUpload, SalesSettingsRead, SalesSettingsUpdate
from app.services.auth_service import AuthService
from app.services.company_service import CompanyService, logo_data_url

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


@router.get("/company/sales-settings", response_model=SalesSettingsRead)
def get_sales_settings(
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return service.get(user.company_id)


@router.put("/company/sales-settings", response_model=SalesSettingsRead)
def update_sales_settings(
    data: SalesSettingsUpdate,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return service.update_sales_settings(user.company_id, data)


@router.get("/company/logo", response_model=LogoRead)
def get_logo(
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return LogoRead(data_url=logo_data_url(service.get(user.company_id)))


@router.put("/company/logo", response_model=LogoRead)
def upload_logo(
    data: LogoUpload,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    company = service.set_logo(user.company_id, data)
    return LogoRead(data_url=logo_data_url(company))


@router.delete("/company/logo", response_model=LogoRead)
def remove_logo(
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    service.remove_logo(user.company_id)
    return LogoRead(data_url=None)
