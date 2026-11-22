"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { journalService } from "@/services";
import { JournalEntry } from "@/types/models";

function entryTotal(entry: JournalEntry): number {
  let total = 0;
  for (const line of entry.lines) {
    total += toNumber(line.debit);
  }
  return total;
}

export default function JournalEntriesPage() {
  const router = useRouter();
  const { company } = useAuth();
  const entries = useLoad(() => journalService.list());

  return (
    <div>
      <PageHeader
        title="Journal entries"
        subtitle="Every transaction in your books. Invoices, payments and expenses create entries automatically."
        actions={
          <LinkButton href="/accounting/journal-entries/new">
            <Plus size={16} /> New journal entry
          </LinkButton>
        }
      />
      <ErrorMessage message={entries.error} />
      {entries.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={entries.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push("/accounting/journal-entries/" + row.id)}
          emptyText="No transactions yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.entry_date) },
            { header: "Type", render: (row) => formatLabel(row.source_type) },
            { header: "Memo", render: (row) => row.memo },
            {
              header: "Accounts",
              render: (row) => (
                <div className="space-y-0.5 text-xs">
                  {row.lines.map((line) => (
                    <div key={line.id} className={toNumber(line.credit) > 0 ? "pl-4 text-gray-500" : ""}>
                      {line.account.name}
                    </div>
                  ))}
                </div>
              ),
            },
            {
              header: "Debit",
              align: "right",
              render: (row) => (
                <div className="space-y-0.5 text-xs">
                  {row.lines.map((line) => (
                    <div key={line.id}>{toNumber(line.debit) > 0 ? formatMoney(line.debit, company?.currency) : " "}</div>
                  ))}
                </div>
              ),
            },
            {
              header: "Credit",
              align: "right",
              render: (row) => (
                <div className="space-y-0.5 text-xs">
                  {row.lines.map((line) => (
                    <div key={line.id}>{toNumber(line.credit) > 0 ? formatMoney(line.credit, company?.currency) : " "}</div>
                  ))}
                </div>
              ),
            },
            { header: "Total", align: "right", render: (row) => formatMoney(entryTotal(row), company?.currency) },
          ]}
        />
      )}
    </div>
  );
}
