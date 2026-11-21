/**
 * Central frontend configuration.
 *
 * Values come from frontend/.env.local. No other file should read
 * process.env directly - import `appConfig` instead.
 */

export const appConfig = {
  appName: process.env.NEXT_PUBLIC_APP_NAME || "DigiBooks",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  locale: process.env.NEXT_PUBLIC_LOCALE || "en-US",
  defaultCurrency: process.env.NEXT_PUBLIC_DEFAULT_CURRENCY || "USD",
  tokenStorageKey: "ledgerly.accessToken",
  sidebarStorageKey: "ledgerly.sidebarOpenGroups",
};
