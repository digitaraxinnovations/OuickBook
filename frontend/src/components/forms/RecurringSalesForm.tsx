"use client";

import { FormEvent, useState } from "react";
import { scheduleToValues } from "@/components/forms/RecurringJournalForm";
import { ScheduleFields, ScheduleValues } from "@/components/forms/ScheduleFields";
import { emptySalesLine, SalesLinesEditor } from "@/components/sales/SalesLinesEditor";
import { emptySalesAmounts, SalesTotals } from "@/components/sales/SalesTotals";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { RecurringScheduleInput, SalesAmountsInput, SalesLineInput } from "@/types/inputs";
import { Account, Customer, Product, RecurringSchedule } from "@/types/models";

interface SavedLine {
  product_id: number | null;
  description: string | null;
  quantity: string;
  rate: string;
}

function templateLines(schedule: RecurringSchedule | null): SalesLineInput[] {
  if (!schedule) {
    return [emptySalesLine()];
  }
  const saved = (schedule.template.lines || []) as SavedLine[];
  return saved.map((line) => ({
    product_id: line.product_id,
    description: line.description || "",
    quantity: String(line.quantity),
    rate: String(line.rate),
  }));
}

function templateAmounts(schedule: RecurringSchedule | null): SalesAmountsInput {
  if (!schedule) {
    return emptySalesAmounts();
  }
  const template = schedule.template;
  return {
    discount_type: (template.discount_type as SalesAmountsInput["discount_type"]) || null,
    discount_value: String(template.discount_value || "0"),
    shipping_amount: String(template.shipping_amount || "0"),
  };
}

interface RecurringSalesFormProps {
  type: "INVOICE" | "SALES_RECEIPT";
  initial: RecurringSchedule | null;
  customers: Customer[];
  products: Product[];
  depositAccounts: Account[];
  currency?: string;
  onSave: (input: RecurringScheduleInput) => Promise<void>;
  onCancel: () => void;
}

/** Recurring invoice or recurring sales receipt template. */
export function RecurringSalesForm({ type, initial, customers, products, depositAccounts, currency, onSave, onCancel }: RecurringSalesFormProps) {
  const template = initial ? initial.template : {};
  const [schedule, setSchedule] = useState<ScheduleValues>(scheduleToValues(initial));
  const [customerId, setCustomerId] = useState(template.customer_id ? String(template.customer_id) : "");
  const [memo, setMemo] = useState(template.memo ? String(template.memo) : "");
  const [moneyAccountId, setMoneyAccountId] = useState(template.money_account_id ? String(template.money_account_id) : "");
  const [lines, setLines] = useState<SalesLineInput[]>(templateLines(initial));
  const [amounts, setAmounts] = useState<SalesAmountsInput>(templateAmounts(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const body: Record<string, unknown> = {
      customer_id: Number(customerId),
      memo: memo,
      lines: lines,
      discount_type: amounts.discount_type,
      discount_value: amounts.discount_value || "0",
      shipping_amount: amounts.shipping_amount || "0",
    };
    if (type === "SALES_RECEIPT") {
      body.money_account_id = moneyAccountId ? Number(moneyAccountId) : null;
    }
    try {
      await onSave({ ...schedule, transaction_type: type, template: body });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <ScheduleFields values={schedule} onChange={setSchedule} startDateLocked={initial !== null && initial.run_count > 0} />
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Customer" required>
          <Select
            required
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Choose a customer"
            options={customers.map((customer) => ({ value: customer.id, label: customer.display_name }))}
          />
        </Field>
        {type === "SALES_RECEIPT" ? (
          <Field label="Deposit to">
            <Select
              value={moneyAccountId}
              onChange={(e) => setMoneyAccountId(e.target.value)}
              placeholder="Undeposited Funds"
              options={depositAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
            />
          </Field>
        ) : (
          <Field label="Message on invoice">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
        )}
      </div>
      <SalesLinesEditor lines={lines} onChange={setLines} products={products} currency={currency} />
      <div className="flex justify-end">
        <SalesTotals lines={lines} amounts={amounts} onChange={setAmounts} currency={currency} />
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={schedule.is_active} onChange={(e) => setSchedule({ ...schedule, is_active: e.target.checked })} />
          Active (uncheck to pause)
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save template"}
        </Button>
      </div>
    </form>
  );
}
