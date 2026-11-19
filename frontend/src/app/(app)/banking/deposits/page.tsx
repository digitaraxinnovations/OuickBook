"use client";

import { Plus } from "lucide-react";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { depositService } from "@/services";

export default function DepositsPage() {
  const { company } = useAuth();
  const deposits = useLoad(() => depositService.list());
  const waiting = useLoad(() => depositService.undeposited());

  let waitingTotal = 0;
  for (const item of waiting.data || []) {
    waitingTotal += Number(item.amount);
  }

  return (
    <div>
      <PageHeader
        title="Bank deposits"
        subtitle="Move customer payments from Undeposited Funds into your bank account."
        actions={
          <LinkButton href="/banking/deposits/new">
            <Plus size={16} /> New deposit
          </LinkButton>
        }
      />
      {(waiting.data || []).length > 0 && (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {(waiting.data || []).length} payment(s) totalling <strong>{formatMoney(waitingTotal, company?.currency)}</strong> are waiting to
          be deposited.
        </div>
      )}
      <ErrorMessage message={deposits.error} />
      {deposits.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={deposits.data || []}
          rowKey={(row) => row.id}
          emptyText="No deposits yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.deposit_date) },
            { header: "Bank account", render: (row) => row.bank_account.name },
            { header: "Items", render: (row) => row.lines.length },
            { header: "Memo", render: (row) => row.memo },
            { header: "Total", align: "right", render: (row) => formatMoney(row.total, company?.currency) },
          ]}
        />
      )}
    </div>
  );
}
