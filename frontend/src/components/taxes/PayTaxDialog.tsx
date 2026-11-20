"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { formatDate, todayString } from "@/lib/format";
import { taxService } from "@/services";
import { Account, TaxPeriod } from "@/types/models";

interface PayTaxDialogProps {
  open: boolean;
  /** The period being paid, or null to pick one. */
  period: TaxPeriod | null;
  /** Periods that still have something owed. */
  duePeriods: TaxPeriod[];
  accounts: Account[];
  onClose: () => void;
  onSaved: () => void;
}

function periodKey(period: TaxPeriod): string {
  return period.agency_id + "|" + period.period_start + "|" + period.period_end;
}

/** Record money paid to a tax agency for one filing period. */
export function PayTaxDialog({ open, period, duePeriods, accounts, onClose, onSaved }: PayTaxDialogProps) {
  const [chosenKey, setChosenKey] = useState(period ? periodKey(period) : "");
  const [amount, setAmount] = useState(period ? period.balance : "");
  const [paymentDate, setPaymentDate] = useState(todayString());
  const [accountId, setAccountId] = useState("");
  const [memo, setMemo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // You can pay any period; the ones with a balance are listed first.
  const choices = period ? [period, ...duePeriods.filter((item) => periodKey(item) !== periodKey(period))] : duePeriods;
  const chosen = choices.find((item) => periodKey(item) === chosenKey) || null;

  const payFromAccounts = accounts.filter((account) => account.detail_type === "Bank" || account.detail_type === "Credit Card");

  function choosePeriod(key: string) {
    setChosenKey(key);
    const found = choices.find((item) => periodKey(item) === key);
    if (found) {
      setAmount(found.balance);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!chosen) {
      setError("Choose the filing period you are paying.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await taxService.recordPayment({
        agency_id: chosen.agency_id,
        period_start: chosen.period_start,
        period_end: chosen.period_end,
        payment_date: paymentDate,
        amount: amount,
        payment_account_id: Number(accountId),
        memo: memo,
      });
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not record the payment.");
      setSaving(false);
    }
  }

  const periodOptions = choices.map((item) => ({
    value: periodKey(item),
    label: item.agency_name + ": " + formatDate(item.period_start) + " - " + formatDate(item.period_end),
  }));

  return (
    <Modal title="Record sales tax payment" open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <Field label="Filing period" required>
          <Select required value={chosenKey} onChange={(e) => choosePeriod(e.target.value)} placeholder="Choose a period" options={periodOptions} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Payment amount" required>
            <TextInput type="number" step="0.01" min="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
          <Field label="Payment date" required>
            <TextInput type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
          </Field>
        </div>
        <Field label="Bank or credit card account" required>
          <Select
            required
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            placeholder="Choose an account"
            options={payFromAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
          />
        </Field>
        <Field label="Memo">
          <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Record payment"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
