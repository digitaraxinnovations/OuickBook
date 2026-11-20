"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { bankingService } from "@/services";
import { ReconcileItem, ReconciliationWorkspace } from "@/types/models";

function Summary({ label, value, highlight }: { label: string; value: string; highlight?: "good" | "bad" }) {
  const color = highlight === "good" ? "text-brand-700" : highlight === "bad" ? "text-red-600" : "text-gray-900";
  return (
    <div>
      <div className="text-xs font-semibold uppercase text-gray-500">{label}</div>
      <div className={"text-xl font-semibold " + color}>{value}</div>
    </div>
  );
}

/** Tick each transaction that is on the statement until the difference is 0. */
export default function ReconcileWorkspacePage() {
  const params = useParams<{ id: string }>();
  const reconciliationId = Number(params.id);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;
  const [workspace, setWorkspace] = useState<ReconciliationWorkspace | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    bankingService
      .workspace(reconciliationId)
      .then((data) => {
        setWorkspace(data);
        setSelected(data.items.filter((item) => item.selected).map((item) => item.journal_line_id));
      })
      .catch((problem) => setError(problem instanceof Error ? problem.message : "Could not load."));
  }, [reconciliationId]);

  if (!workspace) {
    return error ? <ErrorMessage message={error} /> : <Loading />;
  }
  const reconciliation = workspace.reconciliation;

  // Work the numbers out on screen so they change as boxes are ticked.
  let cleared = toNumber(reconciliation.beginning_balance);
  for (const item of workspace.items) {
    if (selected.includes(item.journal_line_id)) {
      cleared += toNumber(item.amount);
    }
  }
  // "+ 0" turns a rounding result of -0 into 0, so the screen never shows "-$0.00".
  const difference = Math.round((toNumber(reconciliation.ending_balance) - cleared) * 100) / 100 + 0;

  function toggle(item: ReconcileItem) {
    if (selected.includes(item.journal_line_id)) {
      setSelected(selected.filter((id) => id !== item.journal_line_id));
    } else {
      setSelected([...selected, item.journal_line_id]);
    }
  }

  async function saveForLater() {
    await bankingService.saveSelection(reconciliationId, selected);
    router.push("/banking/reconcile");
  }

  async function finish() {
    setError(null);
    try {
      await bankingService.saveSelection(reconciliationId, selected);
      await bankingService.finish(reconciliationId);
      router.push("/banking/reconcile/" + reconciliationId + "/report");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not finish.");
    }
  }

  async function cancel() {
    if (window.confirm("Stop this reconciliation? Nothing is changed in your books.")) {
      await bankingService.cancelReconciliation(reconciliationId);
      router.push("/banking/reconcile");
    }
  }

  const increases = workspace.items.filter((item) => toNumber(item.amount) >= 0);
  const decreases = workspace.items.filter((item) => toNumber(item.amount) < 0);

  function itemTable(title: string, items: ReconcileItem[]) {
    return (
      <Card title={title} className="mb-6">
        {items.length === 0 && <p className="text-sm text-gray-500">None.</p>}
        <table className="w-full text-sm">
          <tbody>
            {items.map((item) => (
              <tr key={item.journal_line_id} className="cursor-pointer border-b border-gray-100 hover:bg-brand-50/50" onClick={() => toggle(item)}>
                <td className="w-8 py-2">
                  <input type="checkbox" readOnly checked={selected.includes(item.journal_line_id)} />
                </td>
                <td className="py-2">{formatDate(item.entry_date)}</td>
                <td className="py-2">{item.transaction_type}</td>
                <td className="py-2">{item.description}</td>
                <td className="py-2 text-right">{formatMoney(Math.abs(toNumber(item.amount)), currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    );
  }

  const isCard = reconciliation.account.account_type === "LIABILITY";

  return (
    <div>
      <PageHeader
        title={"Reconcile " + reconciliation.account.name}
        subtitle={"Statement ending " + formatDate(reconciliation.statement_date)}
        actions={
          <>
            <Button variant="secondary" onClick={cancel}>
              Cancel
            </Button>
            <Button variant="secondary" onClick={saveForLater}>
              Save for later
            </Button>
            <Button onClick={finish} disabled={difference !== 0}>
              Finish now
            </Button>
          </>
        }
      />
      <ErrorMessage message={error} />
      <Card className="mb-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Summary label="Beginning balance" value={formatMoney(reconciliation.beginning_balance, currency)} />
          <Summary label="Statement ending balance" value={formatMoney(reconciliation.ending_balance, currency)} />
          <Summary label="Cleared balance" value={formatMoney(cleared, currency)} />
          <Summary label="Difference" value={formatMoney(difference, currency)} highlight={difference === 0 ? "good" : "bad"} />
        </div>
      </Card>
      {itemTable(isCard ? "Charges" : "Deposits and other credits", increases)}
      {itemTable(isCard ? "Payments and credits" : "Checks, payments and other debits", decreases)}
    </div>
  );
}
