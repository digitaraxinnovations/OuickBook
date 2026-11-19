"use client";

import { Play, Plus } from "lucide-react";
import { useState } from "react";
import { RecurringJournalForm } from "@/components/forms/RecurringJournalForm";
import { RecurringSalesForm } from "@/components/forms/RecurringSalesForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, SuccessMessage } from "@/components/ui/Feedback";
import { Field, Select } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel } from "@/lib/format";
import { accountService, customerService, productService, recurringService } from "@/services";
import { RecurringScheduleInput } from "@/types/inputs";
import { RecurringSchedule, RecurringType } from "@/types/models";

const periodNames: Record<string, string> = { DAILY: "day", WEEKLY: "week", MONTHLY: "month", YEARLY: "year" };

const typeOptions = [
  { value: "INVOICE", label: "Invoice" },
  { value: "SALES_RECEIPT", label: "Sales receipt" },
  { value: "JOURNAL_ENTRY", label: "Journal entry" },
];

function describeSchedule(schedule: RecurringSchedule): string {
  const period = periodNames[schedule.frequency];
  if (schedule.interval === 1) {
    return "Every " + period;
  }
  return "Every " + schedule.interval + " " + period + "s";
}

export default function RecurringPage() {
  const { company } = useAuth();
  const schedules = useLoad(() => recurringService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));
  const [editing, setEditing] = useState<RecurringSchedule | null>(null);
  const [formType, setFormType] = useState<RecurringType>("INVOICE");
  const [formOpen, setFormOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const allAccounts = accounts.data || [];
  const accountOptions = allAccounts.map((account) => ({ value: account.id, label: account.full_name }));
  const depositAccounts = allAccounts.filter((account) => account.account_type === "ASSET" && account.system_key !== "accounts_receivable");

  function openNew() {
    setEditing(null);
    setFormType("INVOICE");
    setFormOpen(true);
  }

  function openEdit(schedule: RecurringSchedule) {
    setEditing(schedule);
    setFormType(schedule.transaction_type);
    setFormOpen(true);
  }

  async function save(input: RecurringScheduleInput) {
    if (editing) {
      await recurringService.update(editing.id, input);
    } else {
      await recurringService.create(input);
    }
    setFormOpen(false);
    schedules.reload();
  }

  async function runDue() {
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await recurringService.runDue();
      setMessage(result.created.length === 0 ? "Nothing is due right now." : "Created " + result.created.length + " transaction(s).");
      schedules.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not run the schedules.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Recurring transactions"
        subtitle="Templates that create invoices, sales receipts or journal entries on a schedule (when you click Run due, or by the daily job)."
        actions={
          <>
            <Button variant="secondary" onClick={runDue} disabled={running}>
              <Play size={16} /> {running ? "Running..." : "Run due"}
            </Button>
            <Button onClick={openNew}>
              <Plus size={16} /> New template
            </Button>
          </>
        }
      />
      <ErrorMessage message={error || schedules.error} />
      <SuccessMessage message={message} />
      {schedules.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={schedules.data || []}
          rowKey={(row) => row.id}
          emptyText="No recurring templates yet."
          onRowClick={openEdit}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "Type", render: (row) => formatLabel(row.transaction_type) },
            { header: "Interval", render: (row) => describeSchedule(row) },
            { header: "Previous date", render: (row) => formatDate(row.last_run_date) || "-" },
            { header: "Next date", render: (row) => (row.next_date ? formatDate(row.next_date) : "Finished") },
            { header: "Status", render: (row) => (row.is_active ? "Active" : <span className="text-gray-400">Paused</span>) },
          ]}
        />
      )}
      <Modal title={editing ? "Edit recurring " + formatLabel(formType).toLowerCase() : "New recurring template"} open={formOpen} onClose={() => setFormOpen(false)} wide>
        {!editing && (
          <div className="mb-4 w-60">
            <Field label="Transaction type">
              <Select value={formType} onChange={(e) => setFormType(e.target.value as RecurringType)} options={typeOptions} />
            </Field>
          </div>
        )}
        {formType === "JOURNAL_ENTRY" ? (
          <RecurringJournalForm
            key={(editing ? editing.id : "new") + formType}
            initial={editing}
            accountOptions={accountOptions}
            currency={company?.currency}
            onSave={save}
            onCancel={() => setFormOpen(false)}
          />
        ) : (
          <RecurringSalesForm
            key={(editing ? editing.id : "new") + formType}
            type={formType}
            initial={editing}
            customers={customers.data || []}
            products={products.data || []}
            depositAccounts={depositAccounts}
            currency={company?.currency}
            onSave={save}
            onCancel={() => setFormOpen(false)}
          />
        )}
      </Modal>
    </div>
  );
}
