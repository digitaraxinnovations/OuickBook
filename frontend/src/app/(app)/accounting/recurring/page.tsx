"use client";

import { Play, Plus } from "lucide-react";
import { useState } from "react";
import { RecurringJournalForm } from "@/components/forms/RecurringJournalForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel } from "@/lib/format";
import { accountService, recurringService } from "@/services";
import { RecurringScheduleInput } from "@/types/inputs";
import { RecurringSchedule } from "@/types/models";

const periodNames: Record<string, string> = { DAILY: "day", WEEKLY: "week", MONTHLY: "month", YEARLY: "year" };

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
  const [editing, setEditing] = useState<RecurringSchedule | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const accountOptions = (accounts.data || []).map((account) => ({ value: account.id, label: account.full_name }));

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
      setMessage(
        result.created.length === 0
          ? "Nothing is due right now."
          : "Created " + result.created.length + " transaction(s). See them under Journal entries.",
      );
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
        subtitle="Templates that create transactions on a schedule. Due transactions are created when you click Run due (or by the daily job)."
        actions={
          <>
            <Button variant="secondary" onClick={runDue} disabled={running}>
              <Play size={16} /> {running ? "Running..." : "Run due"}
            </Button>
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus size={16} /> New template
            </Button>
          </>
        }
      />
      <ErrorMessage message={error || schedules.error} />
      {message && <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>}
      {schedules.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={schedules.data || []}
          rowKey={(row) => row.id}
          emptyText="No recurring templates yet."
          onRowClick={(row) => {
            setEditing(row);
            setFormOpen(true);
          }}
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
      <Modal
        title={editing ? "Edit recurring journal entry" : "New recurring journal entry"}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        wide
      >
        <RecurringJournalForm
          key={editing ? editing.id : "new"}
          initial={editing}
          accountOptions={accountOptions}
          currency={company?.currency}
          onSave={save}
          onCancel={() => setFormOpen(false)}
        />
      </Modal>
    </div>
  );
}
