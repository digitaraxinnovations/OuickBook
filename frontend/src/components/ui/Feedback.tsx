import { formatLabel } from "@/lib/format";

export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{message}</div>;
}

export function SuccessMessage({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>;
}

export function Loading({ text = "Loading..." }: { text?: string }) {
  return <div className="py-10 text-center text-sm text-gray-500">{text}</div>;
}

const statusColors: Record<string, string> = {
  OPEN: "bg-blue-50 text-blue-700",
  PENDING: "bg-blue-50 text-blue-700",
  PARTIALLY_PAID: "bg-amber-50 text-amber-700",
  ACCEPTED: "bg-amber-50 text-amber-700",
  PAID: "bg-green-50 text-green-700",
  CLOSED: "bg-green-50 text-green-700",
  REJECTED: "bg-gray-100 text-gray-600",
  VOID: "bg-gray-100 text-gray-500",
  OVERDUE: "bg-red-50 text-red-700",
};

/** Colored label for any invoice or sales form status. */
export function StatusBadge({ status, overdue }: { status: string; overdue?: boolean }) {
  const key = overdue ? "OVERDUE" : status;
  return (
    <span className={"inline-block rounded-full px-2.5 py-0.5 text-xs font-medium " + (statusColors[key] || "bg-gray-100 text-gray-600")}>
      {overdue ? "Overdue" : formatLabel(status)}
    </span>
  );
}
