"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { todayString } from "@/lib/format";
import { PaymentInput } from "@/types/inputs";
import { Account, Invoice, PaymentMethod } from "@/types/models";

export const paymentMethodOptions = [
  { value: "BANK_TRANSFER", label: "Bank transfer" },
  { value: "CASH", label: "Cash" },
  { value: "CHECK", label: "Check" },
  { value: "CREDIT_CARD", label: "Credit card" },
  { value: "OTHER", label: "Other" },
];

interface ReceivePaymentFormProps {
  invoice: Invoice;
  depositAccounts: Account[];
  onSave: (input: PaymentInput) => Promise<void>;
  onCancel: () => void;
}

export function ReceivePaymentForm({ invoice, depositAccounts, onSave, onCancel }: ReceivePaymentFormProps) {
  const form = useFormState<PaymentInput>({
    invoice_id: invoice.id,
    payment_date: todayString(),
    amount: invoice.balance_due,
    payment_method: "BANK_TRANSFER",
    reference_no: "",
    deposit_account_id: null,
    memo: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(form.values);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the payment.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Payment date" required>
          <TextInput type="date" required value={form.values.payment_date} onChange={(e) => form.setField("payment_date", e.target.value)} />
        </Field>
        <Field label="Amount received" required>
          <TextInput type="number" step="0.01" min="0.01" required value={form.values.amount} onChange={(e) => form.setField("amount", e.target.value)} />
        </Field>
        <Field label="Payment method">
          <Select
            value={form.values.payment_method}
            onChange={(e) => form.setField("payment_method", e.target.value as PaymentMethod)}
            options={paymentMethodOptions}
          />
        </Field>
        <Field label="Reference no.">
          <TextInput value={form.values.reference_no} onChange={(e) => form.setField("reference_no", e.target.value)} />
        </Field>
      </div>
      <Field label="Deposit to">
        <Select
          value={form.values.deposit_account_id ?? ""}
          onChange={(e) => form.setField("deposit_account_id", e.target.value ? Number(e.target.value) : null)}
          placeholder="Undeposited Funds (default)"
          options={depositAccounts.map((account) => ({ value: account.id, label: account.name }))}
        />
      </Field>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save payment"}
        </Button>
      </div>
    </form>
  );
}
