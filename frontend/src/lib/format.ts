import { appConfig } from "@/config/app.config";

/** The API sends money as strings like "1250.00". */
export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  return Number(value);
}

export function formatMoney(value: string | number | null | undefined, currency?: string): string {
  return new Intl.NumberFormat(appConfig.locale, {
    style: "currency",
    currency: currency || appConfig.defaultCurrency,
  }).format(toNumber(value));
}

/** "2026-11-20" -> "Nov 20, 2026" */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(appConfig.locale, { year: "numeric", month: "short", day: "numeric" });
}

/** Today's date as "YYYY-MM-DD" (local time). */
export function todayString(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return now.getFullYear() + "-" + month + "-" + day;
}

export function firstDayOfYearString(): string {
  return new Date().getFullYear() + "-01-01";
}

/** "PARTIALLY_PAID" -> "Partially paid" */
export function formatLabel(value: string): string {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}
