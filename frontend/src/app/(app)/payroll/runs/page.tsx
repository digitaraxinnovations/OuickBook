"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate, formatMoney } from "@/lib/format";
import { accountService, payrollService } from "@/services";
import { Account, PaySchedule } from "@/types/models";

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-amber-50 text-amber-800",
  APPROVED: "bg-green-50 text-green-700",
  VOID: "bg-gray-100 text-gray-500",
};

function StartPayrollForm({ schedules, banks, onCancel }: { schedules: PaySchedule[]; banks: Account[]; onCancel: () => void }) {
  const router = useRouter();
  const active = schedules.filter((schedule) => schedule.is_active);
  const [scheduleId, setScheduleId] = useState(active.length > 0 ? String(active[0].id) : "");
  const [bankId, setBankId] = useState(banks.length > 0 ? String(banks[0].id) : "");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [payDate, setPayDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const schedule = active.find((item) => item.id === Number(scheduleId));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const run = await payrollService.createRun({
        pay_schedule_id: scheduleId ? Number(scheduleId) : null,
        period_start: periodStart || null,
        period_end: periodEnd || null,
        pay_date: payDate || null,
        bank_account_id: Number(bankId),
        employee_ids: [],
      });
      router.push("/payroll/runs/" + run.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not start the payroll.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Pay schedule">
          <Select
            value={scheduleId}
            onChange={(e) => setScheduleId(e.target.value)}
            placeholder="No schedule (all employees)"
            options={active.map((item) => ({ value: item.id, label: item.name }))}
          />
        </Field>
        <Field label="Pay from" required>
          <Select required value={bankId} onChange={(e) => setBankId(e.target.value)} placeholder="Choose a bank account" options={banks.map((bank) => ({ value: bank.id, label: bank.full_name }))} />
        </Field>
      </div>
      {schedule && (
        <p className="text-sm text-gray-600">
          Next period: <strong>{formatDate(schedule.next_period_start)} - {formatDate(schedule.next_period_end)}</strong>, paid on{" "}
          <strong>{formatDate(schedule.next_pay_date)}</strong>. Fill in the dates below only to pay a different period.
        </p>
      )}
      <div className="grid grid-cols-3 gap-4">
        <Field label="Period start">
          <TextInput type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
        </Field>
        <Field label="Period end">
          <TextInput type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
        </Field>
        <Field label="Pay date">
          <TextInput type="date" value={payDate} onChange={(e) => setPayDate(e.target.value)} />
        </Field>
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Working out paychecks..." : "Continue"}
        </Button>
      </div>
    </form>
  );
}

export default function PayrollRunsPage() {
  const { company } = useAuth();
  const router = useRouter();
  const runs = useLoad(() => payrollService.runs());
  const schedules = useLoad(() => payrollService.schedules());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [open, setOpen] = useState(false);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setOpen(true);
    }
  }, [openFromMenu]);

  if (schedules.loading || accounts.loading) {
    return <Loading />;
  }
  const banks = (accounts.data || []).filter((account) => account.detail_type === "Bank");

  return (
    <div>
      <PageHeader
        title="Payroll"
        subtitle="Each payroll pays your employees for one pay period."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> Run payroll
          </Button>
        }
      />
      <ErrorMessage message={runs.error} />
      {runs.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={runs.data || []}
          rowKey={(row) => row.id}
          emptyText="No payrolls yet. Add employees and a pay schedule, then run payroll."
          onRowClick={(row) => router.push("/payroll/runs/" + row.id)}
          columns={[
            { header: "Pay date", render: (row) => formatDate(row.pay_date) },
            { header: "Period", render: (row) => formatDate(row.period_start) + " - " + formatDate(row.period_end) },
            { header: "Status", render: (row) => <span className={"rounded-full px-2 py-0.5 text-xs font-medium " + STATUS_STYLES[row.status]}>{row.status.toLowerCase()}</span> },
            { header: "Gross pay", align: "right", render: (row) => formatMoney(row.total_gross, company?.currency) },
            { header: "Net pay", align: "right", render: (row) => formatMoney(row.total_net, company?.currency) },
            { header: "Employer cost", align: "right", render: (row) => formatMoney(row.total_employer_cost, company?.currency) },
          ]}
        />
      )}
      <Modal title="Run payroll" open={open} onClose={() => setOpen(false)}>
        {open && <StartPayrollForm schedules={schedules.data || []} banks={banks} onCancel={() => setOpen(false)} />}
      </Modal>
    </div>
  );
}
