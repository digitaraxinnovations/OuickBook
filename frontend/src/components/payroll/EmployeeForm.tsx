"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { paycheckMethodOptions, payItemKindLabels, payTypeOptions } from "@/config/payroll.config";
import { useFormState } from "@/hooks/useFormState";
import { EmployeeInput } from "@/types/inputs";
import { Employee, PayItem, PaySchedule } from "@/types/models";

function employeeToInput(employee: Employee | null): EmployeeInput {
  return {
    display_name: employee?.display_name || "",
    email: employee?.email || "",
    phone: employee?.phone || "",
    address: employee?.address || "",
    tax_id: employee?.tax_id || "",
    hire_date: employee?.hire_date || null,
    release_date: employee?.release_date || null,
    pay_schedule_id: employee?.pay_schedule_id ?? null,
    pay_type: employee?.pay_type || "HOURLY",
    pay_rate: employee?.pay_rate || "",
    default_hours: employee?.default_hours || "0",
    payment_method: employee?.payment_method || "CHECK",
    is_active: employee ? employee.is_active : true,
    pay_items: employee ? employee.pay_items.map((item) => ({ pay_item_id: item.pay_item_id, amount: item.amount })) : [],
  };
}

interface EmployeeFormProps {
  initial: Employee | null;
  schedules: PaySchedule[];
  payItems: PayItem[];
  onSave: (input: EmployeeInput) => Promise<void>;
  onCancel: () => void;
}

export function EmployeeForm({ initial, schedules, payItems, onSave, onCancel }: EmployeeFormProps) {
  const form = useFormState<EmployeeInput>(employeeToInput(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const values = form.values;
  const isHourly = values.pay_type === "HOURLY";
  const activeItems = payItems.filter((item) => item.is_active);

  function findItem(id: number): PayItem | undefined {
    return payItems.find((item) => item.id === id);
  }

  /** Adding a pay item fills in its usual amount. */
  function chooseItem(index: number, id: string) {
    const item = findItem(Number(id));
    const rows = values.pay_items.map((row, i) => (i === index ? { pay_item_id: Number(id), amount: item ? item.default_amount : row.amount } : row));
    form.setField("pay_items", rows);
  }

  function setItemAmount(index: number, amount: string) {
    form.setField(
      "pay_items",
      values.pay_items.map((row, i) => (i === index ? { ...row, amount: amount } : row)),
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave({
        ...values,
        hire_date: values.hire_date || null,
        release_date: values.release_date || null,
        pay_items: values.pay_items.filter((row) => row.pay_item_id),
      });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name" required>
          <TextInput required value={values.display_name} onChange={(e) => form.setField("display_name", e.target.value)} />
        </Field>
        <Field label="Social security number / tax ID">
          <TextInput value={values.tax_id} onChange={(e) => form.setField("tax_id", e.target.value)} />
        </Field>
        <Field label="Email">
          <TextInput type="email" value={values.email} onChange={(e) => form.setField("email", e.target.value)} />
        </Field>
        <Field label="Phone">
          <TextInput value={values.phone} onChange={(e) => form.setField("phone", e.target.value)} />
        </Field>
      </div>
      <Field label="Address (printed on pay stubs)">
        <TextArea rows={2} value={values.address} onChange={(e) => form.setField("address", e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Hire date">
          <TextInput type="date" value={values.hire_date || ""} onChange={(e) => form.setField("hire_date", e.target.value)} />
        </Field>
        <Field label="Release date">
          <TextInput type="date" value={values.release_date || ""} onChange={(e) => form.setField("release_date", e.target.value)} />
        </Field>
      </div>

      <h3 className="pt-2 text-xs font-semibold uppercase text-gray-500">Pay</h3>
      <div className="grid grid-cols-3 gap-4">
        <Field label="Pay schedule">
          <Select
            value={values.pay_schedule_id ?? ""}
            onChange={(e) => form.setField("pay_schedule_id", e.target.value ? Number(e.target.value) : null)}
            placeholder="None"
            options={schedules.map((schedule) => ({ value: schedule.id, label: schedule.name }))}
          />
        </Field>
        <Field label="Pay type">
          <Select value={values.pay_type} onChange={(e) => form.setField("pay_type", e.target.value)} options={payTypeOptions} />
        </Field>
        <Field label={isHourly ? "Rate per hour" : "Salary per year"} required>
          <TextInput type="number" step="0.01" min="0" required value={values.pay_rate} onChange={(e) => form.setField("pay_rate", e.target.value)} />
        </Field>
        {isHourly && (
          <Field label="Usual hours per pay period">
            <TextInput type="number" step="0.01" min="0" value={values.default_hours} onChange={(e) => form.setField("default_hours", e.target.value)} />
          </Field>
        )}
        <Field label="Paid by">
          <Select value={values.payment_method} onChange={(e) => form.setField("payment_method", e.target.value)} options={paycheckMethodOptions} />
        </Field>
      </div>

      <div className="rounded-md border border-gray-200 p-3">
        <div className="mb-2 text-sm font-medium text-gray-700">On every paycheck</div>
        {values.pay_items.length === 0 && <p className="mb-2 text-sm text-gray-500">No deductions, taxes or extra earnings.</p>}
        {values.pay_items.map((row, index) => {
          const item = findItem(row.pay_item_id);
          return (
            <div key={index} className="mb-2 flex items-center gap-2">
              <Select
                value={row.pay_item_id || ""}
                onChange={(e) => chooseItem(index, e.target.value)}
                placeholder="Choose a pay item"
                options={activeItems.map((option) => ({ value: option.id, label: option.name + " (" + payItemKindLabels[option.kind] + ")" }))}
              />
              <TextInput
                className="w-28!"
                type="number"
                step="0.0001"
                min="0"
                value={row.amount}
                onChange={(e) => setItemAmount(index, e.target.value)}
                aria-label="Amount"
              />
              <span className="w-16 text-sm text-gray-500">{item && item.calculation === "PERCENT" ? "% gross" : "each"}</span>
              <button
                type="button"
                onClick={() => form.setField("pay_items", values.pay_items.filter((_, i) => i !== index))}
                className="text-gray-400 hover:text-red-600"
                aria-label="Remove pay item"
              >
                <Trash2 size={16} />
              </button>
            </div>
          );
        })}
        <Button type="button" variant="ghost" onClick={() => form.setField("pay_items", [...values.pay_items, { pay_item_id: 0, amount: "0" }])}>
          <Plus size={16} /> Add pay item
        </Button>
      </div>

      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={values.is_active} onChange={(e) => form.setField("is_active", e.target.checked)} />
          Active
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}
