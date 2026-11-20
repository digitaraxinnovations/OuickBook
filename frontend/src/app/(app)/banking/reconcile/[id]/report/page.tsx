"use client";

import { Printer } from "lucide-react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { bankingService } from "@/services";
import { ReconcileItem } from "@/types/models";

function ItemList({ title, items, currency }: { title: string; items: ReconcileItem[]; currency?: string }) {
  let total = 0;
  for (const item of items) {
    total += toNumber(item.amount);
  }
  return (
    <div className="mb-6">
      <div className="border-b border-gray-300 pb-1 text-sm font-semibold">
        {title} ({items.length})
      </div>
      {items.map((item) => (
        <div key={item.journal_line_id} className="flex justify-between py-1 pl-4 text-sm">
          <span>
            {formatDate(item.entry_date)} · {item.transaction_type} · {item.description}
          </span>
          <span>{formatMoney(item.amount, currency)}</span>
        </div>
      ))}
      <div className="flex justify-between border-t border-gray-200 pt-1 text-sm font-semibold">
        <span>Total</span>
        <span>{formatMoney(total, currency)}</span>
      </div>
    </div>
  );
}

export default function ReconciliationReportPage() {
  const params = useParams<{ id: string }>();
  const { company } = useAuth();
  const currency = company?.currency;
  const report = useLoad(() => bankingService.report(Number(params.id)), [params.id]);

  if (report.loading) {
    return <Loading />;
  }
  if (!report.data) {
    return <ErrorMessage message={report.error} />;
  }
  const data = report.data;
  const reconciliation = data.reconciliation;

  return (
    <div>
      <PageHeader
        title="Reconciliation report"
        actions={
          <Button variant="secondary" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </Button>
        }
      />
      <Card>
        <div className="mb-6 text-center">
          <div className="text-sm text-gray-500">{company?.name}</div>
          <div className="text-xl font-semibold">{reconciliation.account.name}</div>
          <div className="text-sm text-gray-500">
            Statement ending {formatDate(reconciliation.statement_date)}
            {reconciliation.completed_at ? " · reconciled " + new Date(reconciliation.completed_at).toLocaleDateString() : ""}
          </div>
        </div>
        <div className="mb-6 grid gap-2 text-sm md:grid-cols-2">
          <div className="flex justify-between">
            <span>Beginning balance</span>
            <span>{formatMoney(reconciliation.beginning_balance, currency)}</span>
          </div>
          <div className="flex justify-between">
            <span>Statement ending balance</span>
            <span>{formatMoney(reconciliation.ending_balance, currency)}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>Cleared balance</span>
            <span>{formatMoney(data.cleared_balance, currency)}</span>
          </div>
          <div className="flex justify-between">
            <span>Register balance on {formatDate(reconciliation.statement_date)}</span>
            <span>{formatMoney(data.register_balance, currency)}</span>
          </div>
        </div>
        <ItemList title="Cleared - increases" items={data.cleared_increases} currency={currency} />
        <ItemList title="Cleared - decreases" items={data.cleared_decreases} currency={currency} />
        <ItemList title="Uncleared transactions as of the statement date" items={data.uncleared} currency={currency} />
      </Card>
    </div>
  );
}
