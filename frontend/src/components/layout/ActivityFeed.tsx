"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { useLoad } from "@/hooks/useLoad";
import { platformService } from "@/services";

/** The latest changes anyone made (from the audit log). Hidden if the user's role cannot see it. */
export function ActivityFeed() {
  const log = useLoad(() => platformService.auditLog({}));
  if (log.error || !log.data) {
    return null;
  }
  return (
    <Card
      title="Activity"
      action={
        <Link href="/settings/audit-log" className="text-sm text-brand-700 hover:underline">
          See all
        </Link>
      }
    >
      {log.data.length === 0 && <p className="text-sm text-gray-500">Nothing yet.</p>}
      <ul className="space-y-2 text-sm">
        {log.data.slice(0, 8).map((entry) => (
          <li key={entry.id} className="flex justify-between gap-4">
            <span>
              <span className="font-medium">{entry.user_name}</span> <span className="text-gray-600">{entry.summary.split(":")[0].toLowerCase()}</span>
            </span>
            <span className="whitespace-nowrap text-xs text-gray-400">{new Date(entry.created_at).toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
