/**
 * "What if?" for the cash-flow forecast. Everything is worked out in the
 * browser from the forecast items; nothing is saved or posted.
 */
import { toNumber } from "@/lib/format";
import { DayBalance, Forecast, ForecastItem } from "@/types/models";

export interface Scenario {
  /** This customer pays `delayDays` later than expected. */
  delayCustomerId: number | null;
  delayDays: number;
  /** A one-time purchase. */
  purchaseAmount: number;
  purchaseDate: string;
  /** A new cost every month, e.g. a new hire. */
  monthlyAmount: number;
  monthlyStart: string;
}

export function emptyScenario(startDate: string): Scenario {
  return { delayCustomerId: null, delayDays: 30, purchaseAmount: 0, purchaseDate: startDate, monthlyAmount: 0, monthlyStart: startDate };
}

export function isChanged(scenario: Scenario): boolean {
  return (scenario.delayCustomerId !== null && scenario.delayDays > 0) || scenario.purchaseAmount > 0 || scenario.monthlyAmount > 0;
}

/** "2026-11-28" + days. Done in UTC so daylight saving cannot shift the day. */
export function addDays(date: string, days: number): string {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** The same day in a later month, or that month's last day. */
function addMonths(date: string, months: number): string {
  const [year, month, day] = date.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year, month + months, 0)).getUTCDate();
  return new Date(Date.UTC(year, month - 1 + months, Math.min(day, lastDay))).toISOString().slice(0, 10);
}

export function scenarioItems(forecast: Forecast, scenario: Scenario): ForecastItem[] {
  const items = forecast.items.map((item) => {
    const delayed = item.customer_id !== null && item.customer_id === scenario.delayCustomerId && toNumber(item.amount) > 0;
    return delayed ? { ...item, date: addDays(item.date, Math.max(scenario.delayDays, 0)) } : item;
  });

  const extra = (date: string, amount: number, description: string): ForecastItem => ({
    date,
    amount: String(-amount),
    type: "What if",
    description,
    customer_id: null,
    customer_name: null,
    link: null,
  });

  if (scenario.purchaseAmount > 0 && scenario.purchaseDate >= forecast.start_date) {
    items.push(extra(scenario.purchaseDate, scenario.purchaseAmount, "One-time purchase"));
  }
  if (scenario.monthlyAmount > 0 && scenario.monthlyStart >= forecast.start_date) {
    for (let month = 0; addMonths(scenario.monthlyStart, month) <= forecast.end_date; month++) {
      items.push(extra(addMonths(scenario.monthlyStart, month), scenario.monthlyAmount, "New monthly cost"));
    }
  }

  return items.filter((item) => item.date <= forecast.end_date).sort((a, b) => a.date.localeCompare(b.date));
}

/** The balance at the end of each day (the same sum the server does). */
export function dailyBalances(forecast: Forecast, items: ForecastItem[]): DayBalance[] {
  // Work in cents so repeated adding cannot drift.
  const changes = new Map<string, number>();
  for (const item of items) {
    changes.set(item.date, (changes.get(item.date) || 0) + Math.round(toNumber(item.amount) * 100));
  }
  let cents = Math.round(toNumber(forecast.starting_balance) * 100);
  return forecast.days.map((day) => {
    cents += changes.get(day.date) || 0;
    return { date: day.date, balance: String(cents / 100) };
  });
}

export function lowestDay(days: DayBalance[]): DayBalance {
  return days.reduce((lowest, day) => (toNumber(day.balance) < toNumber(lowest.balance) ? day : lowest), days[0]);
}
