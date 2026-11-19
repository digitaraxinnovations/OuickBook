"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { invoiceService } from "@/services";

const statusFilterOptions = [
  { value: "OPEN", label: "Open" },
  { value: "PARTIALLY_PAID", label: "Partially paid" },
  { value: "PAID", label: "Paid" },
  { value: "VOID", label: "Void" },
];

export default function InvoicesPage() {
  const { company } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const invoices = useLoad(() => invoiceService.listSummaries({ status: status }), [status]);
  const currency = company?.currency;

  return (
    <div>
      <PageHeader
        title="Invoices"
        subtitle="Bills you send to customers. Click an invoice to view it or receive a payment."
        actions={
          <LinkButton href="/sales/invoices/new">
            <Plus size={16} /> Create invoice
          </LinkButton>
        }
      />
      <div className="mb-4 w-56">
        <Select value={status} onChange={(e) => setStatus(e.target.value)} placeholder="All statuses" options={statusFilterOptions} />
      </div>
      <ErrorMessage message={invoices.error} />
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
