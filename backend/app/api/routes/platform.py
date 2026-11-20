"""Companies, users, invitations, settings, currencies, audit log, search, recent and data import/export."""

from datetime import date

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    get_audit_log_service,
    get_integration_service,
    get_notification_service,
    get_currency_service,
    get_current_user,
    get_data_transfer_service,
    get_membership_service,
    get_recent_service,
    get_search_service,
    get_settings_service,
)
from app.models import User
from app.schemas.platform import (
    AcceptInvitation,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    Notification,
    WebhookDeliveryRead,
    WebhookRead,
    WebhookWrite,
    AdvancedSettingsRead,
    AdvancedSettingsUpdate,
    AuditLogRead,
    CompanyMembership,
    CurrencyRead,
    CurrencyWrite,
    ExchangeRateRead,
    ExchangeRateWrite,
    ImportRequest,
    ImportResult,
    InvitationCreate,
    InvitationInfo,
    InvitationRead,
    MemberRead,
    MemberUpdate,
    NewCompanyRequest,
    RecentTransaction,
    RoleInfo,
    SearchResult,
)
from app.schemas.auth import TokenResponse
from app.services.currency_service import CurrencyService
from app.services.integration_service import IntegrationService
from app.services.notification_service import NotificationService
from app.services.data_transfer_service import DataTransferService
from app.services.membership_service import MembershipService
from app.services.platform_service import AuditLogService, RecentService, SearchService, SettingsService

router = APIRouter(tags=["Company, users and platform"])

CurrentUser = Depends(get_current_user)
Memberships = Depends(get_membership_service)


# ---------- companies ----------

@router.get("/companies", response_model=list[CompanyMembership])
def my_companies(user: User = CurrentUser, service: MembershipService = Memberships):
    return service.companies(user)


@router.post("/companies", response_model=list[CompanyMembership], status_code=status.HTTP_201_CREATED)
def create_company(data: NewCompanyRequest, user: User = CurrentUser, service: MembershipService = Memberships):
    """Add another company and switch to it."""
    service.create_company(user, data.name)
    return service.companies(user)


@router.post("/companies/{company_id}/switch", response_model=list[CompanyMembership])
def switch_company(company_id: int, user: User = CurrentUser, service: MembershipService = Memberships):
    service.switch_company(user, company_id)
    return service.companies(user)


# ---------- users and invitations ----------

@router.get("/users/roles", response_model=list[RoleInfo])
def roles(user: User = CurrentUser, service: MembershipService = Memberships):
    return service.roles()


@router.get("/users", response_model=list[MemberRead])
def list_users(user: User = CurrentUser, service: MembershipService = Memberships):
    return service.members(user.company_id)


@router.put("/users/{user_id}", response_model=list[MemberRead])
def update_user(user_id: int, data: MemberUpdate, user: User = CurrentUser, service: MembershipService = Memberships):
    return service.update_member(user.company_id, user_id, data)


@router.get("/invitations", response_model=list[InvitationRead])
def list_invitations(user: User = CurrentUser, service: MembershipService = Memberships):
    return service.invitations(user.company_id)


@router.post("/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
def invite(data: InvitationCreate, user: User = CurrentUser, service: MembershipService = Memberships):
    return service.invite(user.company_id, user, data)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invitation(invitation_id: int, user: User = CurrentUser, service: MembershipService = Memberships):
    service.cancel_invitation(user.company_id, invitation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Opened from the email link - no sign-in needed.
@router.get("/auth/invitations/{token}", response_model=InvitationInfo)
def invitation_info(token: str, service: MembershipService = Memberships):
    return service.invitation_info(token)


@router.post("/auth/invitations/{token}/accept", response_model=TokenResponse)
def accept_invitation(token: str, data: AcceptInvitation, service: MembershipService = Memberships):
    return TokenResponse(access_token=service.accept(token, data))


# ---------- settings ----------

@router.get("/company/advanced-settings", response_model=AdvancedSettingsRead)
def get_advanced_settings(user: User = CurrentUser, service: SettingsService = Depends(get_settings_service)):
    return service.get(user.company_id)


@router.put("/company/advanced-settings", response_model=AdvancedSettingsRead)
def update_advanced_settings(data: AdvancedSettingsUpdate, user: User = CurrentUser, service: SettingsService = Depends(get_settings_service)):
    return service.update(user.company_id, data)


# ---------- currencies ----------

@router.get("/currencies", response_model=list[CurrencyRead])
def list_currencies(user: User = CurrentUser, service: CurrencyService = Depends(get_currency_service)):
    return service.list(user.company_id)


@router.post("/currencies", response_model=CurrencyRead, status_code=status.HTTP_201_CREATED)
def add_currency(data: CurrencyWrite, user: User = CurrentUser, service: CurrencyService = Depends(get_currency_service)):
    return service.add(user.company_id, data)


@router.get("/exchange-rates", response_model=list[ExchangeRateRead])
def list_rates(currency_code: str | None = None, user: User = CurrentUser, service: CurrencyService = Depends(get_currency_service)):
    return service.rates(user.company_id, currency_code)


@router.post("/exchange-rates", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def set_rate(data: ExchangeRateWrite, user: User = CurrentUser, service: CurrencyService = Depends(get_currency_service)):
    return service.set_rate(user.company_id, data)


@router.post("/exchange-rates/refresh")
def refresh_rates(user: User = CurrentUser, service: CurrencyService = Depends(get_currency_service)):
    """Download today's rates from the rates service (EXT)."""
    return {"saved": service.refresh_from_provider(user.company_id, date.today())}


# ---------- audit log ----------

@router.get("/audit-log", response_model=list[AuditLogRead])
def audit_log(
    start_date: date | None = None,
    end_date: date | None = None,
    user_id: int | None = None,
    entity_type: str | None = None,
    user: User = CurrentUser,
    service: AuditLogService = Depends(get_audit_log_service),
):
    return service.list(user.company_id, start_date, end_date, user_id, entity_type)


# ---------- search and recent ----------

@router.get("/search", response_model=list[SearchResult])
def search(q: str, user: User = CurrentUser, service: SearchService = Depends(get_search_service)):
    return service.search(user.company_id, q)


@router.get("/recent", response_model=list[RecentTransaction])
def recent(user: User = CurrentUser, service: RecentService = Depends(get_recent_service)):
    return service.recent(user.company_id)


# ---------- import / export ----------

@router.get("/data/{name}/export")
def export_data(name: str, user: User = CurrentUser, service: DataTransferService = Depends(get_data_transfer_service)):
    """customers, vendors, accounts or journal-entries as a CSV file."""
    content = service.export_csv(user.company_id, name)
    headers = {"Content-Disposition": f'attachment; filename="{name}.csv"'}
    return Response(content=content, media_type="text/csv", headers=headers)


@router.post("/data/{name}/import", response_model=ImportResult)
def import_data(name: str, data: ImportRequest, user: User = CurrentUser, service: DataTransferService = Depends(get_data_transfer_service)):
    return service.import_csv(user.company_id, name, data.content)


# ---------- notifications and activity ----------

@router.get("/notifications", response_model=list[Notification])
def notifications(user: User = CurrentUser, service: NotificationService = Depends(get_notification_service)):
    return service.list(user.company_id)


# ---------- API keys and webhooks (settings area) ----------

Integrations = Depends(get_integration_service)


@router.get("/company/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(user: User = CurrentUser, service: IntegrationService = Integrations):
    return service.api_keys(user.company_id)


@router.post("/company/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(data: ApiKeyCreate, user: User = CurrentUser, service: IntegrationService = Integrations):
    record, key = service.create_api_key(user.company_id, user, data.name)
    return ApiKeyCreated(id=record.id, name=record.name, prefix=record.prefix, last_used_at=None, is_active=True, key=key)


@router.post("/company/api-keys/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: int, user: User = CurrentUser, service: IntegrationService = Integrations):
    service.revoke_api_key(user.company_id, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/company/webhooks", response_model=list[WebhookRead])
def list_webhooks(user: User = CurrentUser, service: IntegrationService = Integrations):
    return service.webhooks(user.company_id)


@router.post("/company/webhooks", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
def create_webhook(data: WebhookWrite, user: User = CurrentUser, service: IntegrationService = Integrations):
    return service.save_webhook(user.company_id, data.url, data.events, data.is_active)


@router.put("/company/webhooks/{webhook_id}", response_model=WebhookRead)
def update_webhook(webhook_id: int, data: WebhookWrite, user: User = CurrentUser, service: IntegrationService = Integrations):
    return service.save_webhook(user.company_id, data.url, data.events, data.is_active, webhook_id)


@router.delete("/company/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int, user: User = CurrentUser, service: IntegrationService = Integrations):
    service.delete_webhook(user.company_id, webhook_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/company/webhook-deliveries", response_model=list[WebhookDeliveryRead])
def webhook_deliveries(user: User = CurrentUser, service: IntegrationService = Integrations):
    return service.deliveries(user.company_id)

