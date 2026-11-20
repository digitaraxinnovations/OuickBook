/** Report date ranges ("This month", "Last year"...), the same ones the backend uses for saved reports. */

export const dateRangeOptions = [
  { value: "this_month", label: "This month" },
  { value: "last_month", label: "Last month" },
  { value: "this_quarter", label: "This quarter" },
  { value: "last_quarter", label: "Last quarter" },
  { value: "this_year", label: "This year" },
  { value: "last_year", label: "Last year" },
  { value: "custom", label: "Custom" },
];

function dayText(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return day.getFullYear() + "-" + month + "-" + date;
}

/** [start, end] as "YYYY-MM-DD" for a named range, counted from today. */
export function resolveDateRange(range: string): [string, string] | null {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const quarterFirstMonth = Math.floor(month / 3) * 3;
  switch (range) {
    case "this_month":
      return [dayText(new Date(year, month, 1)), dayText(new Date(year, month + 1, 0))];
    case "last_month":
      return [dayText(new Date(year, month - 1, 1)), dayText(new Date(year, month, 0))];
    case "this_quarter":
      return [dayText(new Date(year, quarterFirstMonth, 1)), dayText(new Date(year, quarterFirstMonth + 3, 0))];
    case "last_quarter":
      return [dayText(new Date(year, quarterFirstMonth - 3, 1)), dayText(new Date(year, quarterFirstMonth, 0))];
    case "this_year":
      return [dayText(new Date(year, 0, 1)), dayText(new Date(year, 11, 31))];
    case "last_year":
      return [dayText(new Date(year - 1, 0, 1)), dayText(new Date(year - 1, 11, 31))];
    default:
      return null;
  }
}
