"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, todayString } from "@/lib/format";
import { bankingService } from "@/services";
import { Reconciliation } from "@/types/models";

export default function ReconcilePage() {
  const { company } = useAuth();
  const currency = company?.currency;
  const router = useRouter();
  const accounts = useLoad(() => bankingService.accounts());
  const [accountId, setAccountId] = useState("");
  const [statementDate, setStatementDate] = useState(todayString());
  const [endingBalance, setEndingBalance] = useState("");
  const [error, setError] = useState<string | null>(null);

  const history = useLoad(() => (accountId ? bankingService.reconciliations(Number(accountId)) : Promise.resolve([])), [accountId]);
  const discrepancies = useLoad(() => (accountId ? bankingService.discrepancies(Number(accountId)) : Promise.resolve([])), [accountId]);

  useEffect(() => {
    if (!accountId && accounts.data && accounts.data.length > 0) {
      setAccountId(String(accounts.data[0].account.id));
    }
  }, [accountId, accounts.data]);

  if (accounts.loading) {
    return <Loading />;
  }

  const inProgress = (history.data || []).find((item) => item.status === "IN_PROGRESS");
  const lastCompleted = (history.data || []).find((item) => item.status === "COMPLETED");

  async function start(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const reconciliation = await bankingService.startReconciliation(Number(accountId), statementDate, endingBalance);
      router.push("/banking/reconcile/" + reconciliation.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not start.");
    }
  }

  async function undo(reconciliation: Reconciliation) {
    if (!window.confirm("Undo the reconciliation of " + formatDate(reconciliation.statement_date) + "? Its transactions become unreconciled.")) {
      return;
    }
    setError(null);
    try {
      await bankingService.undoReconciliation(reconciliation.id);
      history.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not undo.");
    }
  }

  return (
    <div>
      <PageHeader title="Reconcile" subtitle="Check your books against your bank or credit card statement." />
      <ErrorMessage message={error} />
      <Card className="mb-6">
        <form onSubmit={start} className="grid items-end gap-4 md:grid-cols-4">
          <Field label="Account">
            <Select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              options={(accounts.data || []).map((item) => ({ value: item.account.id, label: item.account.name }))}
            />
          </Field>
          <Field label="Statement ending date" required>
            <TextInput type="date" required value={statementDate} onChange={(e) => setStatementDate(e.target.value)} />
          </Field>
          <Field label="Statement ending balance" required>
            <TextInput type="number" step="0.01" required value={endingBalance} onChange={(e) => setEndingBalance(e.target.value)} />
          </Field>
          <Button type="submit" disabled={!accountId}>
            {inProgress ? "Resume reconciling" : "Start reconciling"}
          </Button>
        </form>
        <p className="mt-3 text-sm text-gray-500">
          Beginning balance: {formatMoney(lastCompleted ? lastCompleted.ending_balance : 0, currency)}
          {lastCompleted ? " (from the statement of " + formatDate(lastCompleted.statement_date) + ")" : " (first reconciliation)"}
        </p>
      </Card>

      {(discrepancies.data || []).length > 0 && (
        <Card title="Reconciliation discrepancies" className="mb-6 border-red-200">
          <p className="mb-3 text-sm text-red-700">These reconciled transactions were changed afterwards, so earlier reconciliations no longer match the statements.</p>
          <DataTable
            rows={discrepancies.data || []}
            rowKey={(row) => row.reconciliation_id + "-" + row.entry_date + row.description}
            columns={[
              { header: "Statement", render: (row) => formatDate(row.statement_date) },
              { header: "Transaction date", render: (row) => formatDate(row.entry_date) },
              { header: "Description", render: (row) => row.description },
              { header: "Change", render: (row) => row.change + " on " + formatDate(row.changed_on) },
              { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
            ]}
          />
        </Card>
      )}

      <h2 className="mb-3 text-lg font-semibold">History</h2>
      <DataTable
        rows={history.data || []}
        rowKey={(row) => row.id}
        emptyText="This account has not been reconciled yet."
        columns={[
          { header: "Statement date", render: (row) => formatDate(row.statement_date) },
          { header: "Beginning", align: "right", render: (row) => formatMoney(row.beginning_balance, currency) },
          { header: "Ending", align: "right", render: (row) => formatMoney(row.ending_balance, currency) },
          { header: "Status", render: (row) => <StatusBadge status={row.status === "COMPLETED" ? "CLOSED" : row.status === "UNDONE" ? "VOID" : "OPEN"} /> },
          {
            header: "",
            align: "right",
            render: (row) => (
              <span className="flex justify-end gap-3 text-sm">
                {row.status === "IN_PROGRESS" && (
                  <button className="text-brand-700 hover:underline" onClick={() => router.push("/banking/reconcile/" + row.id)}>
                    Resume
                  </button>
                )}
                {row.status === "COMPLETED" && (
                  <>
                    <button className="text-brand-700 hover:underline" onClick={() => router.push("/banking/reconcile/" + row.id + "/report")}>
                      Report
                    </button>
                    {lastCompleted && lastCompleted.id === row.id && (
                      <button className="text-gray-500 hover:text-red-600" onClick={() => undo(row)}>
                        Undo
                      </button>
                    )}
                  </>
                )}
              </span>
            ),
          },
        ]}
      />
    </div>
  );
}
