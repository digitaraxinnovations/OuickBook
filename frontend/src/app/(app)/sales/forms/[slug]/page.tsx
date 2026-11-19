"use client";

import { Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { LinkButton } from "@/components/ui/Button";
import { Column, DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { findFormBySlug, SalesFormConfig } from "@/config/sales-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { salesDocumentService } from "@/services";
import { SalesDocumentSummary } from "@/types/models";

const statusOptions = [
  { value: "PENDING", label: "Pending" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "OPEN", label: "Open" },
  { value: "CLOSED", label: "Closed" },
  { value: "PAID", label: "Paid" },
  { value: "VOID", label: "Void" },
];

function buildColumns(form: SalesFormConfig, currency?: string): Column<SalesDocumentSummary>[] {
  const columns: Column<SalesDocumentSummary>[] = [
    { header: "Date", render: (row) => formatDate(row.doc_date) },
    { header: "No.", render: (row) => <span className="font-medium">{row.doc_number}</span> },
    { header: "Customer", render: (row) => row.customer.display_name },
  ];
  if (form.hasExpirationDate) {
    columns.push({ header: "Expires", render: (row) => formatDate(row.expiration_date) });
  }
  columns.push({ header: "Status", render: (row) => <StatusBadge status={row.status} /> });
  if (form.type === "ESTIMATE") {
    columns.push({ header: "Not invoiced", align: "right", render: (row) => formatMoney(row.remaining, currency) });
  }
  if (form.type === "CREDIT_MEMO") {
    columns.push({ header: "Credit left", align: "right", render: (row) => formatMoney(row.remaining, currency) });
  }
  columns.push({ header: "Total", align: "right", render: (row) => formatMoney(row.total, currency) });
  return columns;
}

/** List page for estimates, sales receipts, credit memos, refunds and delayed charges/credits. */
export default function SalesFormListPage() {
  const params = useParams<{ slug: string }>();
  const form = findFormBySlug(params.slug);
  const router = useRouter();
  const { company } = useAuth();
  const [status, setStatus] = useState("");

  const documents = useLoad(
    () => (form ? salesDocumentService.listByType(form.type, { status: status }) : Promise.resolve([])),
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
          <LinkButton href={"/sales/forms/" + form.slug + "/new"}>
            <Plus size={16} /> New {form.title.toLowerCase()}
          </LinkButton>
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
          onRowClick={(row) => router.push("/sales/forms/" + form.slug + "/" + row.id)}
          emptyText={"No " + form.plural.toLowerCase() + " yet."}
          columns={buildColumns(form, company?.currency)}
        />
      )}
    </div>
  );
}
