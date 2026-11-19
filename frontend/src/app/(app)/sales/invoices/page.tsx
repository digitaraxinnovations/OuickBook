"use client";

import { BellRing, Plus, Timer } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge, SuccessMessage } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { invoiceService } from "@/services";
import { BatchResult } from "@/types/models";

const statusFilterOptions = [
  { value: "OPEN", label: "Open" },
  { value: "PARTIALLY_PAID", label: "Partially paid" },
  { value: "PAID", label: "Paid" },
  { value: "VOID", label: "Void" },
];

function describeBatch(result: BatchResult): string {
  return result.details.length > 0 ? result.details.join(" · ") : "Nothing to do right now.";
}

export default function InvoicesPage() {
  const { company } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const invoices = useLoad(() => invoiceService.listSummaries({ status: status }), [status]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const currency = company?.currency;

  async function runBatch(action: () => Promise<BatchResult>) {
    setMessage(null);
    setError(null);
    try {
      setMessage(describeBatch(await action()));
      invoices.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Invoices"
        subtitle="Bills you send to customers. Click an invoice to view, email or receive a payment."
        actions={
          <>
            <Button variant="secondary" onClick={() => runBatch(() => invoiceService.applyLateFees())} title="Uses the late fee rules in Settings → Sales">
              <Timer size={16} /> Apply late fees
            </Button>
            <Button variant="secondary" onClick={() => runBatch(() => invoiceService.sendReminders())} title="Uses the reminder rules in Settings → Sales">
              <BellRing size={16} /> Send reminders
            </Button>
            <LinkButton href="/sales/invoices/new">
              <Plus size={16} /> Create invoice
            </LinkButton>
          </>
        }
      />
      <ErrorMessage message={error || invoices.error} />
      <SuccessMessage message={message} />
      <div className="mb-4 w-56">
        <Select value={status} onChange={(e) => setStatus(e.target.value)} placeholder="All statuses" options={statusFilterOptions} />
      </div>
      {invoices.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={invoices.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push("/sales/invoices/" + row.id)}
          emptyText="No invoices found."
          columns={[
            { header: "Date", render: (row) => formatDate(row.invoice_date) },
            { header: "No.", render: (row) => <span className="font-medium">{row.invoice_number}</span> },
            { header: "Customer", render: (row) => row.customer.display_name },
            { header: "Due date", render: (row) => formatDate(row.due_date) },
            { header: "Status", render: (row) => <StatusBadge status={row.status} overdue={row.is_overdue} /> },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.total, currency) },
            { header: "Balance", align: "right", render: (row) => formatMoney(row.balance_due, currency) },
          ]}
        />
      )}
    </div>
  );
}
