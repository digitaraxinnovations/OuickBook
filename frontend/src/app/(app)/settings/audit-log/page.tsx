"use client";

import { useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { useLoad } from "@/hooks/useLoad";
import { platformService } from "@/services";
import { AuditEntry } from "@/types/models";

const RECORD_TYPES = [
  "Account",
  "Bill payment",
  "Budget",
  "Company settings",
  "Customer",
  "Employee",
  "Expense",
  "Invoice",
  "Journal entry",
  "Payment",
  "Payroll",
  "Product or service",
  "Sales form",
  "Time entry",
  "Transfer",
  "User access",
  "Vendor",
  "Vendor form",
];

function changesText(entry: AuditEntry): string {
  if (!entry.changes) {
    return "";
  }
  return Object.entries(entry.changes)
    .map(([field, [before, after]]) => field.replace(/_/g, " ") + ": " + (before ?? "(empty)") + " → " + (after ?? "(empty)"))
    .join("; ");
}

/** Who added, changed or deleted what - written automatically for every save. */
export default function AuditLogPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [recordType, setRecordType] = useState("");
  const log = useLoad(
    () => platformService.auditLog({ start_date: startDate || undefined, end_date: endDate || undefined, entity_type: recordType || undefined }),
    [startDate, endDate, recordType],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div className="w-44">
          <Field label="From">
            <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
        </div>
        <div className="w-44">
          <Field label="To">
            <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Field>
        </div>
        <div className="w-56">
          <Field label="Record">
            <Select value={recordType} onChange={(e) => setRecordType(e.target.value)} placeholder="All records" options={RECORD_TYPES.map((item) => ({ value: item, label: item }))} />
          </Field>
        </div>
      </div>
      <ErrorMessage message={log.error} />
      {log.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={log.data || []}
          rowKey={(row) => row.id}
          emptyText="Nothing in the log for these filters."
          columns={[
            { header: "When", render: (row) => new Date(row.created_at).toLocaleString() },
            { header: "User", render: (row) => row.user_name },
            { header: "Event", render: (row) => row.summary },
            { header: "Changes", render: (row) => <span className="text-xs text-gray-600">{changesText(row)}</span> },
          ]}
        />
      )}
    </div>
  );
}
