"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, toNumber } from "@/lib/format";
import { accountService, trackingService } from "@/services";
import { Account, Budget } from "@/types/models";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_OPTIONS = MONTHS.map((name, index) => ({ value: index + 1, label: name }));

/** {account_id: 12 amounts as text} - one row per income and expense account. */
type Grid = Record<number, string[]>;

function gridFrom(budget: Budget, accounts: Account[]): Grid {
  const grid: Grid = {};
  for (const account of accounts) {
    grid[account.id] = ["", "", "", "", "", "", "", "", "", "", "", ""];
  }
  for (const line of budget.lines) {
    grid[line.account_id] = line.months.map((amount) => (toNumber(amount) === 0 ? "" : String(toNumber(amount))));
  }
  return grid;
}

function rowTotal(months: string[]): number {
  let total = 0;
  for (const value of months) {
    total += toNumber(value);
  }
  return total;
}

function BudgetVsActualView({ budgetId, currency }: { budgetId: number; currency?: string }) {
  const [firstMonth, setFirstMonth] = useState(1);
  const [lastMonth, setLastMonth] = useState(12);
  const result = useLoad(() => trackingService.budgetVsActual(budgetId, firstMonth, lastMonth), [budgetId, firstMonth, lastMonth]);
  const data = result.data;

  return (
    <Card title="Budget vs actual">
      <div className="mb-4 flex items-center gap-2 text-sm">
        From
        <Select className="w-24!" value={firstMonth} onChange={(e) => setFirstMonth(Number(e.target.value))} options={MONTH_OPTIONS} />
        to
        <Select className="w-24!" value={lastMonth} onChange={(e) => setLastMonth(Number(e.target.value))} options={MONTH_OPTIONS} />
      </div>
      <ErrorMessage message={result.error} />
      {result.loading || !data ? (
        <Loading />
      ) : (
        <>
          <DataTable
            rows={data.rows}
            rowKey={(row) => row.account_id}
            emptyText="Nothing budgeted or posted in these months."
            columns={[
              { header: "Account", render: (row) => row.account_name },
              { header: "Type", render: (row) => (row.account_type === "INCOME" ? "Income" : "Expense") },
              { header: "Budget", align: "right", render: (row) => formatMoney(row.budget, currency) },
              { header: "Actual", align: "right", render: (row) => formatMoney(row.actual, currency) },
              {
                header: "Over / under",
                align: "right",
                render: (row) => {
                  // More income or less expense than planned is good (green).
                  const difference = toNumber(row.difference);
                  const good = row.account_type === "INCOME" ? difference >= 0 : difference <= 0;
                  return <span className={good ? "text-green-700" : "text-red-600"}>{formatMoney(difference, currency)}</span>;
                },
              },
              { header: "% of budget", align: "right", render: (row) => (row.percent_of_budget !== null ? toNumber(row.percent_of_budget) + "%" : "-") },
            ]}
          />
          <div className="mt-4 flex justify-end gap-8 text-sm">
            <span>
              Budgeted net income: <strong>{formatMoney(data.budget_net_income, currency)}</strong>
            </span>
            <span>
              Actual net income: <strong>{formatMoney(data.actual_net_income, currency)}</strong>
            </span>
          </div>
        </>
      )}
    </Card>
  );
}

export default function BudgetPage() {
  const params = useParams();
  const router = useRouter();
  const budgetId = Number(params.id);
  const { company } = useAuth();
  const budget = useLoad(() => trackingService.budget(budgetId), [budgetId]);
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [grid, setGrid] = useState<Grid | null>(null);
  const [view, setView] = useState<"edit" | "compare">("edit");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const budgetAccounts = (accounts.data || []).filter((account) => account.account_type === "INCOME" || account.account_type === "EXPENSE");

  useEffect(() => {
    if (budget.data && accounts.data && grid === null) {
      setGrid(gridFrom(budget.data, budgetAccounts));
    }
  }, [budget.data, accounts.data, grid, budgetAccounts]);

  if (budget.loading || accounts.loading || !grid) {
    return <Loading />;
  }
  if (!budget.data) {
    return <ErrorMessage message={budget.error || "Budget not found."} />;
  }
  const current = budget.data;
  const currentGrid: Grid = grid;

  function setCell(accountId: number, monthIndex: number, value: string) {
    const months = currentGrid[accountId].map((old, i) => (i === monthIndex ? value : old));
    setGrid({ ...currentGrid, [accountId]: months });
  }

  /** Copy the first month across the year. */
  function fillRow(accountId: number) {
    const first = currentGrid[accountId][0];
    setGrid({ ...currentGrid, [accountId]: currentGrid[accountId].map(() => first) });
  }

  async function save() {
    setSaving(true);
    setError(null);
    setMessage(null);
    const lines = [];
    for (const account of budgetAccounts) {
      const months = currentGrid[account.id];
      if (rowTotal(months) !== 0 || months.some((value) => toNumber(value) !== 0)) {
        lines.push({ account_id: account.id, months: months.map((value) => value || "0") });
      }
    }
    try {
      await trackingService.saveBudget(
        { name: current.name, fiscal_year: current.fiscal_year, class_id: current.class_id, location_id: current.location_id, lines: lines },
        current.id,
      );
      setMessage("Budget saved.");
      setRefreshKey(refreshKey + 1);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the budget.");
    }
    setSaving(false);
  }

  async function deleteBudget() {
    if (window.confirm("Delete this budget?")) {
      await trackingService.deleteBudget(current.id);
      router.push("/accounting/budgets");
    }
  }

  let incomeTotal = 0;
  let expenseTotal = 0;
  for (const account of budgetAccounts) {
    if (account.account_type === "INCOME") {
      incomeTotal += rowTotal(currentGrid[account.id]);
    } else {
      expenseTotal += rowTotal(currentGrid[account.id]);
    }
  }

  return (
    <div>
      <PageHeader
        title={current.name}
        subtitle={"Year " + current.fiscal_year}
        actions={
          <div className="flex gap-2">
            <Button variant={view === "edit" ? "primary" : "secondary"} onClick={() => setView("edit")}>
              Edit amounts
            </Button>
            <Button variant={view === "compare" ? "primary" : "secondary"} onClick={() => setView("compare")}>
              Budget vs actual
            </Button>
          </div>
        }
      />
      <ErrorMessage message={error} />
      {message && <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</div>}

      {view === "compare" ? (
        <BudgetVsActualView key={refreshKey} budgetId={current.id} currency={company?.currency} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1200px] text-sm">
              <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="w-52 py-2">Account</th>
                  {MONTHS.map((name) => (
                    <th key={name} className="py-2 text-center">
                      {name}
                    </th>
                  ))}
                  <th className="w-24 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {budgetAccounts.map((account) => (
                  <tr key={account.id} className="border-b border-gray-100">
                    <td className="py-1 pr-2">
                      <div className="font-medium">{account.name}</div>
                      <button type="button" onClick={() => fillRow(account.id)} className="text-xs text-brand-700 hover:underline">
                        Copy Jan across
                      </button>
                    </td>
                    {currentGrid[account.id].map((value, monthIndex) => (
                      <td key={monthIndex} className="px-0.5 py-1">
                        <TextInput
                          className="px-1! text-right"
                          type="number"
                          step="0.01"
                          value={value}
                          onChange={(e) => setCell(account.id, monthIndex, e.target.value)}
                          aria-label={account.name + " " + MONTHS[monthIndex]}
                        />
                      </td>
                    ))}
                    <td className="py-1 text-right font-medium">{formatMoney(rowTotal(currentGrid[account.id]), company?.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm">
              Income {formatMoney(incomeTotal, company?.currency)} − expenses {formatMoney(expenseTotal, company?.currency)} ={" "}
              <strong>{formatMoney(incomeTotal - expenseTotal, company?.currency)}</strong> planned net income
            </div>
            <div className="flex gap-2">
              <Button variant="danger" onClick={deleteBudget}>
                Delete
              </Button>
              <Button onClick={save} disabled={saving}>
                {saving ? "Saving..." : "Save budget"}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
