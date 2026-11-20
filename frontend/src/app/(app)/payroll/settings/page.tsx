"use client";

import { Plus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { frequencyOptions, liabilityKinds, payItemKindLabels, payItemKindOptions } from "@/config/payroll.config";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, toNumber } from "@/lib/format";
import { accountService, payrollService } from "@/services";
import { Account, PayItem, PaySchedule } from "@/types/models";

interface FormProps<T> {
  initial: T | null;
  onSaved: () => void;
  onCancel: () => void;
}

function SaveButtons({ onCancel }: { onCancel: () => void }) {
  return (
    <div className="flex justify-end gap-2">
      <Button type="button" variant="secondary" onClick={onCancel}>
        Cancel
      </Button>
      <Button type="submit">Save</Button>
    </div>
  );
}

function ScheduleForm({ initial, onSaved, onCancel }: FormProps<PaySchedule>) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [frequency, setFrequency] = useState<string>(initial ? initial.frequency : "BIWEEKLY");
  const [periodEnd, setPeriodEnd] = useState(initial ? initial.next_period_end : "");
  const [payDate, setPayDate] = useState(initial ? initial.next_pay_date : "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const input = { name: name, frequency: frequency, next_period_end: periodEnd, next_pay_date: payDate, is_active: isActive };
      await payrollService.saveSchedule(input, initial?.id);
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name" required>
          <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Every other Friday" />
        </Field>
        <Field label="How often" required>
          <Select value={frequency} onChange={(e) => setFrequency(e.target.value)} options={frequencyOptions} />
        </Field>
        <Field label="End of the next pay period" required>
          <TextInput type="date" required value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
        </Field>
        <Field label="Next pay day" required>
          <TextInput type="date" required value={payDate} onChange={(e) => setPayDate(e.target.value)} />
        </Field>
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
      <SaveButtons onCancel={onCancel} />
    </form>
  );
}

interface PayItemFormProps extends FormProps<PayItem> {
  accounts: Account[];
}

function PayItemForm({ initial, accounts, onSaved, onCancel }: PayItemFormProps) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [kind, setKind] = useState<string>(initial ? initial.kind : "DEDUCTION");
  const [calculation, setCalculation] = useState<string>(initial ? initial.calculation : "PERCENT");
  const [amount, setAmount] = useState(initial ? String(toNumber(initial.default_amount)) : "");
  const [expenseId, setExpenseId] = useState(initial?.expense_account ? String(initial.expense_account.id) : "");
  const [liabilityId, setLiabilityId] = useState(initial?.liability_account ? String(initial.liability_account.id) : "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [error, setError] = useState<string | null>(null);

  const usesExpense = kind === "EARNING" || kind === "EMPLOYER_TAX" || kind === "EMPLOYER_CONTRIBUTION";
  const usesLiability = liabilityKinds.includes(kind);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await payrollService.savePayItem(
        {
          name: name,
          kind: kind,
          calculation: calculation,
          default_amount: amount || "0",
          expense_account_id: usesExpense && expenseId ? Number(expenseId) : null,
          liability_account_id: usesLiability && liabilityId ? Number(liabilityId) : null,
          is_active: isActive,
        },
        initial?.id,
      );
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  function accountOptions(type: string) {
    return accounts.filter((account) => account.account_type === type).map((account) => ({ value: account.id, label: account.full_name }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name" required>
          <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. 401(k)" />
        </Field>
        <Field label="Kind" required>
          <Select value={kind} onChange={(e) => setKind(e.target.value)} options={payItemKindOptions} disabled={initial !== null} />
        </Field>
        <Field label="Usual amount">
          <Select
            value={calculation}
            onChange={(e) => setCalculation(e.target.value)}
            options={[
              { value: "PERCENT", label: "Percent of gross pay" },
              { value: "FIXED", label: "Fixed amount per paycheck" },
            ]}
          />
        </Field>
        <Field label={calculation === "PERCENT" ? "Percent" : "Amount"}>
          <TextInput type="number" step="0.0001" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        {usesExpense && (
          <Field label="Expense account">
            <Select
              value={expenseId}
              onChange={(e) => setExpenseId(e.target.value)}
              placeholder={kind === "EARNING" ? "Wages & Salaries" : "Payroll Taxes & Benefits"}
              options={accountOptions("EXPENSE")}
            />
          </Field>
        )}
        {usesLiability && (
          <Field label="Liability account">
            <Select value={liabilityId} onChange={(e) => setLiabilityId(e.target.value)} placeholder="Payroll Liabilities" options={accountOptions("LIABILITY")} />
          </Field>
        )}
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
      <SaveButtons onCancel={onCancel} />
    </form>
  );
}

type Editing = { kind: "schedule"; record: PaySchedule | null } | { kind: "item"; record: PayItem | null } | null;

export default function PayrollSettingsPage() {
  const schedules = useLoad(() => payrollService.schedules());
  const items = useLoad(() => payrollService.payItems());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [editing, setEditing] = useState<Editing>(null);

  if (schedules.loading || items.loading || accounts.loading) {
    return <Loading />;
  }

  const frequencyLabels: Record<string, string> = {};
  for (const option of frequencyOptions) {
    frequencyLabels[option.value] = option.label;
  }

  function afterSave() {
    setEditing(null);
    schedules.reload();
    items.reload();
  }

  function amountText(item: PayItem): string {
    if (item.calculation === "PERCENT") {
      return toNumber(item.default_amount) + "% of gross";
    }
    return toNumber(item.default_amount).toFixed(2) + " per paycheck";
  }

  return (
    <div>
      <PageHeader
        title="Payroll settings"
        subtitle="Pay schedules, and everything on a paycheck besides regular pay: deductions, taxes and employer contributions."
      />
      <ErrorMessage message={schedules.error || items.error} />
      <Card
        title="Pay schedules"
        className="mb-6"
        action={
          <Button variant="ghost" onClick={() => setEditing({ kind: "schedule", record: null })}>
            <Plus size={16} /> Add schedule
          </Button>
        }
      >
        <DataTable
          rows={schedules.data || []}
          rowKey={(row) => row.id}
          emptyText="Add a pay schedule to run payroll."
          onRowClick={(row) => setEditing({ kind: "schedule", record: row })}
          columns={[
            { header: "Name", render: (row) => row.name },
            { header: "Pay", render: (row) => frequencyLabels[row.frequency] },
            { header: "Next period", render: (row) => formatDate(row.next_period_start) + " - " + formatDate(row.next_period_end) },
            { header: "Next pay day", render: (row) => formatDate(row.next_pay_date) },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
          ]}
        />
      </Card>
      <Card
        title="Pay items"
        action={
          <Button variant="ghost" onClick={() => setEditing({ kind: "item", record: null })}>
            <Plus size={16} /> Add pay item
          </Button>
        }
      >
        <p className="mb-3 text-sm text-gray-600">
          Payroll taxes are not worked out automatically (no payroll service is connected). Add each tax you withhold or pay as a pay item,
          e.g. &quot;Federal income tax&quot; at 10% of gross.
        </p>
        <DataTable
          rows={items.data || []}
          rowKey={(row) => row.id}
          emptyText="No pay items yet."
          onRowClick={(row) => setEditing({ kind: "item", record: row })}
          columns={[
            { header: "Name", render: (row) => row.name },
            { header: "Kind", render: (row) => payItemKindLabels[row.kind] },
            { header: "Usual amount", render: (row) => amountText(row) },
            { header: "Account", render: (row) => (row.liability_account || row.expense_account)?.name || "Default" },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
          ]}
        />
      </Card>
      <Modal title={editing?.kind === "schedule" ? "Pay schedule" : "Pay item"} open={editing !== null} onClose={() => setEditing(null)}>
        {editing && editing.kind === "schedule" && <ScheduleForm initial={editing.record} onSaved={afterSave} onCancel={() => setEditing(null)} />}
        {editing && editing.kind === "item" && (
          <PayItemForm initial={editing.record} accounts={accounts.data || []} onSaved={afterSave} onCancel={() => setEditing(null)} />
        )}
      </Modal>
    </div>
  );
}
