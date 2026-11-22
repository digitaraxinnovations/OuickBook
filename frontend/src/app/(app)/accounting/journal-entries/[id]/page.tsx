"use client";

import { useParams } from "next/navigation";
import { AttachmentsPanel } from "@/components/ui/AttachmentsPanel";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { journalService } from "@/services";

/** One journal entry: its lines, and files attached to it (e.g. the calculation behind it). */
export default function JournalEntryDetailPage() {
  const params = useParams<{ id: string }>();
  const entryId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;
  const entry = useLoad(() => journalService.get(entryId), [entryId]);

  if (entry.loading) {
    return <Loading />;
  }
  if (!entry.data) {
    return <ErrorMessage message={entry.error} />;
  }
  const data = entry.data;
  let debits = 0;
  let credits = 0;
  for (const line of data.lines) {
    debits += toNumber(line.debit);
    credits += toNumber(line.credit);
  }

  return (
    <div>
      <PageHeader title={"Journal entry " + data.id} subtitle={formatDate(data.entry_date) + " - " + formatLabel(data.source_type)} />
      <Card>
        <div className="grid gap-6 text-sm md:grid-cols-3">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Date</div>
            <div className="mt-1">{formatDate(data.entry_date)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Created by</div>
            <div className="mt-1">{formatLabel(data.source_type)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Memo</div>
            <div className="mt-1">{data.memo || "-"}</div>
          </div>
        </div>
        <table className="mt-6 w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Account</th>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Debit</th>
              <th className="py-2 text-right">Credit</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id} className="border-b border-gray-100">
                <td className="py-2">{line.account.name}</td>
                <td className="py-2">{line.description}</td>
                <td className="py-2 text-right">{toNumber(line.debit) ? formatMoney(line.debit, currency) : ""}</td>
                <td className="py-2 text-right">{toNumber(line.credit) ? formatMoney(line.credit, currency) : ""}</td>
              </tr>
            ))}
            <tr className="font-semibold">
              <td className="py-2" colSpan={2}>
                Total
              </td>
              <td className="py-2 text-right">{formatMoney(debits, currency)}</td>
              <td className="py-2 text-right">{formatMoney(credits, currency)}</td>
            </tr>
          </tbody>
        </table>
      </Card>
      <AttachmentsPanel entityType="JOURNAL_ENTRY" entityId={data.id} />
    </div>
  );
}
