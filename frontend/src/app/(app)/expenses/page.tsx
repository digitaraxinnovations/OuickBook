"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { expenseService } from "@/services";
import { Expense } from "@/types/models";

/** One category name, or "Split" when the expense has several lines. */
function categoryLabel(expense: Expense): string {
  if (expense.lines.length === 1) {
    return expense.lines[0].account.name;
  }
  return "Split (" + expense.lines.length + " categories)";
}

function typeLabel(expense: Expense): string {
  if (expense.kind === "CHECK") {
    return expense.check_number ? "Check " + expense.check_number : "Check (to print)";
  }
  return "Expense";
}

export default function ExpensesPage() {
  const { company } = useAuth();
  const router = useRouter();
  const expenses = useLoad(() => expenseService.list());

  return (
    <div>
      <PageHeader
        title="Expenses & checks"
        subtitle="Money you spent right away from a bank or credit card account."
        actions={
          <>
            <LinkButton href="/expenses/new?kind=CHECK" variant="secondary">
              Write check
            </LinkButton>
            <LinkButton href="/expenses/new">
              <Plus size={16} /> New expense
            </LinkButton>
          </>
        }
      />
      <ErrorMessage message={expenses.error} />
      {expenses.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={expenses.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push("/expenses/" + row.id)}
          emptyText="No expenses recorded yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.expense_date) },
            { header: "Type", render: (row) => typeLabel(row) },
            { header: "Payee", render: (row) => row.vendor?.display_name || "-" },
            { header: "Category", render: (row) => categoryLabel(row) },
            { header: "Paid from", render: (row) => row.payment_account.name },
            {
              header: "Total",
              align: "right",
              render: (row) => (row.is_void ? <span className="text-gray-400">Void</span> : formatMoney(row.total, company?.currency)),
            },
          ]}
        />
      )}
    </div>
  );
}
