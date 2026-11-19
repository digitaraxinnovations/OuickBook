"use client";

import { Plus } from "lucide-react";
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

export default function ExpensesPage() {
  const { company } = useAuth();
  const expenses = useLoad(() => expenseService.list());

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="Money you spent from a bank or credit card account."
        actions={
          <LinkButton href="/expenses/new">
            <Plus size={16} /> New expense
          </LinkButton>
        }
      />
      <ErrorMessage message={expenses.error} />
      {expenses.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={expenses.data || []}
          rowKey={(row) => row.id}
          emptyText="No expenses recorded yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.expense_date) },
            { header: "Payee", render: (row) => row.vendor?.display_name || "-" },
            { header: "Category", render: (row) => categoryLabel(row) },
            { header: "Paid from", render: (row) => row.payment_account.name },
            { header: "Memo", render: (row) => row.memo },
            { header: "Total", align: "right", render: (row) => formatMoney(row.total, company?.currency) },
          ]}
        />
      )}
    </div>
  );
}
