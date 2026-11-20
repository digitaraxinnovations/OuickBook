"use client";

import { Printer } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { AttachmentsPanel } from "@/components/ui/AttachmentsPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatLabel, formatMoney } from "@/lib/format";
import { checkService, expenseService } from "@/services";

export default function ExpenseDetailPage() {
  const params = useParams<{ id: string }>();
  const expenseId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;
  const expense = useLoad(() => expenseService.get(expenseId), [expenseId]);
  const [error, setError] = useState<string | null>(null);

  if (expense.loading) {
    return <Loading />;
  }
  if (!expense.data) {
    return <ErrorMessage message={expense.error} />;
  }
  const data = expense.data;
  const isCheck = data.kind === "CHECK";

  async function voidExpense() {
    if (!window.confirm("Void this " + (isCheck ? "check" : "expense") + "? It is reversed in your books.")) {
      return;
    }
    setError(null);
    try {
      await expenseService.void(data.id);
      expense.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not void.");
    }
  }

  async function printCheck() {
    setError(null);
    try {
      openBlobInNewTab(await checkService.reprint("EXPENSE", data.id));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not print.");
    }
  }

  let title = "Expense";
  if (isCheck) {
    title = data.check_number ? "Check " + data.check_number : "Check (waiting to print)";
  }

  return (
    <div>
      <PageHeader
        title={title + (data.is_void ? " - VOID" : "")}
        actions={
          <>
            {isCheck && data.check_number && (
              <Button variant="secondary" onClick={printCheck}>
                <Printer size={16} /> Print check
              </Button>
            )}
            {!data.is_void && (
              <Button variant="danger" onClick={voidExpense}>
                Void
              </Button>
            )}
          </>
        }
      />
      <ErrorMessage message={error} />
      <Card>
        <div className="grid gap-6 text-sm md:grid-cols-4">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Payee</div>
            <div className="mt-1">{data.vendor?.display_name || "-"}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Date</div>
            <div className="mt-1">{formatDate(data.expense_date)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Paid from</div>
            <div className="mt-1">{data.payment_account.name}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Method</div>
            <div className="mt-1">{formatLabel(data.payment_method)}</div>
          </div>
        </div>
        <table className="mt-6 w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Category</th>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id} className="border-b border-gray-100">
                <td className="py-2">{line.account.name}</td>
                <td className="py-2">{line.description}</td>
                <td className="py-2 text-right">{formatMoney(line.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 flex justify-between">
          <div className="text-sm text-gray-600">{data.memo}</div>
          <div className="text-lg font-semibold">Total {formatMoney(data.total, currency)}</div>
        </div>
      </Card>
      <AttachmentsPanel entityType="EXPENSE" entityId={data.id} />
    </div>
  );
}
