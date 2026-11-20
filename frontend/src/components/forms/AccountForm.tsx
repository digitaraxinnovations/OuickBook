"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { AccountInput } from "@/types/inputs";
import { Account, AccountType } from "@/types/models";

export const accountTypeOptions = [
  { value: "ASSET", label: "Asset" },
  { value: "LIABILITY", label: "Liability" },
  { value: "EQUITY", label: "Equity" },
  { value: "INCOME", label: "Income" },
  { value: "EXPENSE", label: "Expense" },
];

function accountToInput(account: Account | null): AccountInput {
  return {
    name: account?.name || "",
    code: account?.code || "",
    account_type: account?.account_type || "EXPENSE",
    detail_type: account?.detail_type || "",
    description: account?.description || "",
    parent_id: account ? account.parent_id : null,
    box_1099: account ? account.box_1099 : null,
    tax_line: account ? account.tax_line : null,
    is_active: account ? account.is_active : true,
  };
}

interface AccountFormProps {
  initial: Account | null;
  allAccounts: Account[];
  /** {"NEC_1": "1099-NEC Box 1: ..."} */
  boxes1099: Record<string, string>;
  /** {"SCHC_18": "Line 18 - Office expense"} */
  taxLines: Record<string, string>;
  onSave: (input: AccountInput) => Promise<void>;
  onCancel: () => void;
}

export function AccountForm({ initial, allAccounts, boxes1099, taxLines, onSave, onCancel }: AccountFormProps) {
  const form = useFormState<AccountInput>(accountToInput(initial));

  // A sub-account's parent must have the same type, and cannot be the account itself.
  const parentOptions = allAccounts
    .filter((account) => account.account_type === form.values.account_type && account.id !== initial?.id)
    .map((account) => ({ value: account.id, label: account.full_name }));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(form.values);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Account type" required>
          <Select
            value={form.values.account_type}
            disabled={initial !== null}
            onChange={(e) => {
              form.setField("account_type", e.target.value as AccountType);
              form.setField("parent_id", null);
            }}
            options={accountTypeOptions}
          />
        </Field>
        <Field label="Detail type" required>
          <TextInput
            required
            placeholder="e.g. Bank, Office Expenses"
            value={form.values.detail_type}
            onChange={(e) => form.setField("detail_type", e.target.value)}
          />
        </Field>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Field label="Number">
          <TextInput value={form.values.code} onChange={(e) => form.setField("code", e.target.value)} />
        </Field>
        <div className="col-span-2">
          <Field label="Name" required>
            <TextInput required value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} />
          </Field>
        </div>
      </div>
      <Field label="Sub-account of">
        <Select
          value={form.values.parent_id ?? ""}
          onChange={(e) => form.setField("parent_id", e.target.value ? Number(e.target.value) : null)}
          placeholder="(none - top-level account)"
          options={parentOptions}
        />
      </Field>
      {form.values.account_type === "EXPENSE" && (
        <Field label="1099 box (payments to contractors from this account)">
          <Select
            value={form.values.box_1099 ?? ""}
            onChange={(e) => form.setField("box_1099", e.target.value || null)}
            placeholder="Not reported on a 1099"
            options={Object.keys(boxes1099).map((key) => ({ value: key, label: boxes1099[key] }))}
          />
        </Field>
      )}
      {(form.values.account_type === "INCOME" || form.values.account_type === "EXPENSE") && (
        <Field label="Income tax category">
          <Select
            value={form.values.tax_line ?? ""}
            onChange={(e) => form.setField("tax_line", e.target.value || null)}
            placeholder="Not assigned"
            options={Object.keys(taxLines).map((key) => ({ value: key, label: taxLines[key] }))}
          />
        </Field>
      )}
      <Field label="Description">
        <TextArea rows={2} value={form.values.description} onChange={(e) => form.setField("description", e.target.value)} />
      </Field>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.values.is_active} onChange={(e) => form.setField("is_active", e.target.checked)} />
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
