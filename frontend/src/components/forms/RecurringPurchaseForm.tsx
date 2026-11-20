"use client";

import { FormEvent, useState } from "react";
import { emptyPurchaseLine, PurchaseLinesEditor, purchaseLinesTotal } from "@/components/purchases/PurchaseLinesEditor";
import { scheduleToValues } from "@/components/forms/RecurringJournalForm";
import { ScheduleFields, ScheduleValues } from "@/components/forms/ScheduleFields";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { formatMoney } from "@/lib/format";
import { PurchaseLineInput, RecurringScheduleInput } from "@/types/inputs";
import { Account, RecurringSchedule, Vendor } from "@/types/models";

interface SavedLine {
  account_id: number;
  description: string | null;
  quantity?: string;
  rate?: string;
  amount?: string;
  customer_id: number | null;
}

/** Bills store quantity + rate; expenses store an amount. The editor shows both as quantity x rate. */
function templateLines(schedule: RecurringSchedule | null): PurchaseLineInput[] {
  if (!schedule) {
    return [emptyPurchaseLine()];
  }
  const saved = (schedule.template.lines || []) as SavedLine[];
  return saved.map((line) => ({
    account_id: line.account_id,
    description: line.description || "",
    quantity: String(line.quantity || "1"),
    rate: String(line.rate || line.amount || ""),
    customer_id: line.customer_id,
  }));
}

interface RecurringPurchaseFormProps {
  type: "BILL" | "EXPENSE";
  initial: RecurringSchedule | null;
  vendors: Vendor[];
  accounts: Account[];
  customerOptions: SelectOption[];
  currency?: string;
  onSave: (input: RecurringScheduleInput) => Promise<void>;
  onCancel: () => void;
}

/** Recurring bill (e.g. monthly rent bill) or recurring expense (e.g. a monthly card subscription). */
export function RecurringPurchaseForm({ type, initial, vendors, accounts, customerOptions, currency, onSave, onCancel }: RecurringPurchaseFormProps) {
  const template = initial ? initial.template : {};
  const [schedule, setSchedule] = useState<ScheduleValues>(scheduleToValues(initial));
  const [vendorId, setVendorId] = useState(template.vendor_id ? String(template.vendor_id) : "");
  const [paymentAccountId, setPaymentAccountId] = useState(template.payment_account_id ? String(template.payment_account_id) : "");
  const [memo, setMemo] = useState(template.memo ? String(template.memo) : "");
  const [lines, setLines] = useState<PurchaseLineInput[]>(templateLines(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const expenseAccounts = accounts.filter((account) => account.account_type === "EXPENSE");
  const otherAccounts = accounts.filter((account) => account.account_type !== "EXPENSE");
  const categoryOptions = [...expenseAccounts, ...otherAccounts].map((account) => ({ value: account.id, label: account.full_name }));
  const payFrom = accounts.filter((account) => account.detail_type === "Bank" || account.detail_type === "Credit Card");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    let body: Record<string, unknown>;
    if (type === "BILL") {
      body = { vendor_id: Number(vendorId), memo: memo, lines: lines };
    } else {
      const payAccount = payFrom.find((account) => account.id === Number(paymentAccountId));
      body = {
        vendor_id: vendorId ? Number(vendorId) : null,
        payment_account_id: Number(paymentAccountId),
        payment_method: payAccount && payAccount.detail_type === "Credit Card" ? "CREDIT_CARD" : "BANK_TRANSFER",
        memo: memo,
        lines: lines.map((line) => ({
          account_id: line.account_id,
          description: line.description,
          amount: (Number(line.quantity) * Number(line.rate)).toFixed(2),
          customer_id: line.customer_id,
        })),
      };
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
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Vendor" required={type === "BILL"}>
          <Select
            required={type === "BILL"}
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
            placeholder={type === "BILL" ? "Choose a vendor" : "(none)"}
            options={vendors.map((vendor) => ({ value: vendor.id, label: vendor.display_name }))}
          />
        </Field>
        {type === "EXPENSE" && (
          <Field label="Pay from" required>
            <Select
              required
              value={paymentAccountId}
              onChange={(e) => setPaymentAccountId(e.target.value)}
              placeholder="Bank or card"
              options={payFrom.map((account) => ({ value: account.id, label: account.full_name }))}
            />
          </Field>
        )}
        <Field label="Memo">
          <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
        </Field>
      </div>
      <PurchaseLinesEditor lines={lines} onChange={setLines} categoryOptions={categoryOptions} customerOptions={customerOptions} currency={currency} />
      <div className="text-right text-lg font-semibold">Total {formatMoney(purchaseLinesTotal(lines), currency)}</div>
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
