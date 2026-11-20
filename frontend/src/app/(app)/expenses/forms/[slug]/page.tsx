"use client";

import { Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { LinkButton } from "@/components/ui/Button";
import { Column, DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { findPurchaseFormBySlug, PurchaseFormConfig } from "@/config/purchase-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { purchaseService } from "@/services";
import { PurchaseDocumentSummary } from "@/types/models";

const statusOptions = [
  { value: "OPEN", label: "Open" },
  { value: "PARTIALLY_PAID", label: "Partially paid" },
  { value: "PAID", label: "Paid" },
  { value: "CLOSED", label: "Closed" },
  { value: "VOID", label: "Void" },
];

function buildColumns(form: PurchaseFormConfig, currency?: string): Column<PurchaseDocumentSummary>[] {
  const columns: Column<PurchaseDocumentSummary>[] = [
    { header: "Date", render: (row) => formatDate(row.doc_date) },
    { header: "No.", render: (row) => row.doc_number || "-" },
    { header: "Vendor", render: (row) => row.vendor.display_name },
  ];
  if (form.hasDueDate) {
    columns.push({ header: "Due date", render: (row) => formatDate(row.due_date) });
  }
  columns.push({ header: "Status", render: (row) => <StatusBadge status={row.status} overdue={row.is_overdue} /> });
  if (form.type !== "PURCHASE_ORDER") {
    columns.push({ header: form.type === "BILL" ? "Open balance" : "Credit left", align: "right", render: (row) => formatMoney(row.balance, currency) });
  }
  columns.push({ header: "Total", align: "right", render: (row) => formatMoney(row.total, currency) });
  return columns;
}

export default function PurchaseFormListPage() {
  const params = useParams<{ slug: string }>();
  const form = findPurchaseFormBySlug(params.slug);
  const router = useRouter();
  const { company } = useAuth();
  const [status, setStatus] = useState("");
  const documents = useLoad(
    () => (form ? purchaseService.listByType(form.type, { status: status }) : Promise.resolve([])),
    [params.slug, status],
  );

  if (!form) {
    return <ErrorMessage message="This page does not exist." />;
  }

  return (
    <div>
      <PageHeader
        title={form.plural}
        subtitle={form.description}
        actions={
          <>
            {form.type === "BILL" && (
              <LinkButton href="/expenses/pay-bills" variant="secondary">
                Pay bills
              </LinkButton>
            )}
            <LinkButton href={"/expenses/forms/" + form.slug + "/new"}>
              <Plus size={16} /> New {form.title.toLowerCase()}
            </LinkButton>
          </>
        }
      />
      <div className="mb-4 w-56">
        <Select value={status} onChange={(e) => setStatus(e.target.value)} placeholder="All statuses" options={statusOptions} />
      </div>
      <ErrorMessage message={documents.error} />
      {documents.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={documents.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push("/expenses/forms/" + form.slug + "/" + row.id)}
          emptyText={"No " + form.plural.toLowerCase() + " yet."}
          columns={buildColumns(form, company?.currency)}
        />
      )}
    </div>
  );
}
