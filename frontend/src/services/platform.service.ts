import { ApiClient } from "@/lib/api-client";
import {
  AdvancedSettings,
  Integrations,
  ApiKeyItem,
  AppNotification,
  WebhookDeliveryItem,
  WebhookItem,
  AuditEntry,
  CompanyMembership,
  CurrencyItem,
  ExchangeRateItem,
  ImportResult,
  Invitation,
  InvitationInfo,
  Member,
  RecentTransaction,
  RoleInfo,
  SearchResult,
  UserRole,
} from "@/types/models";

/** Companies, users, invitations, settings, currencies, audit log, search and import/export. */
export class PlatformService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- companies -----

  companies(): Promise<CompanyMembership[]> {
    return this.api.get<CompanyMembership[]>("/companies");
  }

  createCompany(name: string): Promise<CompanyMembership[]> {
    return this.api.post<CompanyMembership[]>("/companies", { name: name });
  }

  switchCompany(companyId: number): Promise<CompanyMembership[]> {
    return this.api.post<CompanyMembership[]>("/companies/" + companyId + "/switch");
  }

  // ----- users and invitations -----

  roles(): Promise<RoleInfo[]> {
    return this.api.get<RoleInfo[]>("/users/roles");
  }

  users(): Promise<Member[]> {
    return this.api.get<Member[]>("/users");
  }

  updateUser(userId: number, role: UserRole, isActive: boolean): Promise<Member[]> {
    return this.api.put<Member[]>("/users/" + userId, { role: role, is_active: isActive });
  }

  invitations(): Promise<Invitation[]> {
    return this.api.get<Invitation[]>("/invitations");
  }

  invite(email: string, role: UserRole): Promise<Invitation> {
    return this.api.post<Invitation>("/invitations", { email: email, role: role });
  }

  cancelInvitation(id: number): Promise<void> {
    return this.api.delete<void>("/invitations/" + id);
  }

  invitationInfo(token: string): Promise<InvitationInfo> {
    return this.api.get<InvitationInfo>("/auth/invitations/" + token);
  }

  acceptInvitation(token: string, fullName: string, password: string): Promise<{ access_token: string }> {
    return this.api.post<{ access_token: string }>("/auth/invitations/" + token + "/accept", { full_name: fullName || null, password: password });
  }

  // ----- settings -----

  advancedSettings(): Promise<AdvancedSettings> {
    return this.api.get<AdvancedSettings>("/company/advanced-settings");
  }

  saveAdvancedSettings(input: Record<string, unknown>): Promise<AdvancedSettings> {
    return this.api.put<AdvancedSettings>("/company/advanced-settings", input);
  }

  // ----- currencies -----

  currencies(): Promise<CurrencyItem[]> {
    return this.api.get<CurrencyItem[]>("/currencies");
  }

  addCurrency(code: string, name: string): Promise<CurrencyItem> {
    return this.api.post<CurrencyItem>("/currencies", { code: code, name: name });
  }

  exchangeRates(): Promise<ExchangeRateItem[]> {
    return this.api.get<ExchangeRateItem[]>("/exchange-rates");
  }

  setExchangeRate(currencyCode: string, rateDate: string, rate: string): Promise<ExchangeRateItem> {
    return this.api.post<ExchangeRateItem>("/exchange-rates", { currency_code: currencyCode, rate_date: rateDate, rate: rate });
  }

  refreshExchangeRates(): Promise<{ saved: number }> {
    return this.api.post<{ saved: number }>("/exchange-rates/refresh");
  }

  // ----- audit log, search, recent -----

  auditLog(query: { start_date?: string; end_date?: string; entity_type?: string }): Promise<AuditEntry[]> {
    return this.api.get<AuditEntry[]>("/audit-log", query);
  }

  search(text: string): Promise<SearchResult[]> {
    return this.api.get<SearchResult[]>("/search", { q: text });
  }

  recent(): Promise<RecentTransaction[]> {
    return this.api.get<RecentTransaction[]>("/recent");
  }

  // ----- import / export -----

  exportData(name: string): Promise<Blob> {
    return this.api.getBlob("/data/" + name + "/export");
  }

  importData(name: string, content: string): Promise<ImportResult> {
    return this.api.post<ImportResult>("/data/" + name + "/import", { content: content });
  }

  // ----- notifications, API keys, webhooks -----

  notifications(): Promise<AppNotification[]> {
    return this.api.get<AppNotification[]>("/notifications");
  }

  apiKeys(): Promise<ApiKeyItem[]> {
    return this.api.get<ApiKeyItem[]>("/company/api-keys");
  }

  createApiKey(name: string): Promise<ApiKeyItem & { key: string }> {
    return this.api.post<ApiKeyItem & { key: string }>("/company/api-keys", { name: name });
  }

  revokeApiKey(id: number): Promise<void> {
    return this.api.post<void>("/company/api-keys/" + id + "/revoke");
  }

  webhooks(): Promise<WebhookItem[]> {
    return this.api.get<WebhookItem[]>("/company/webhooks");
  }

  saveWebhook(url: string, events: string[]): Promise<WebhookItem> {
    return this.api.post<WebhookItem>("/company/webhooks", { url: url, events: events, is_active: true });
  }

  deleteWebhook(id: number): Promise<void> {
    return this.api.delete<void>("/company/webhooks/" + id);
  }

  webhookDeliveries(): Promise<WebhookDeliveryItem[]> {
    return this.api.get<WebhookDeliveryItem[]>("/company/webhook-deliveries");
  }

  /** Which outside services are connected (and which are the built-in simulations). */
  integrations(): Promise<Integrations> {
    return this.api.get<Integrations>("/company/integrations");
  }
}
