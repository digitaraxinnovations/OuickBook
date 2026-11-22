"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { SimulatedBadge } from "@/components/ui/SimulatedBadge";
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
  /** File the return electronically through the tax provider (and pay what the period owes). */
  eFile?: boolean;
  simulated?: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function periodKey(period: TaxPeriod): string {
  return period.agency_id + "|" + period.period_start + "|" + period.period_end;
}

/** Record money paid to a tax agency for one filing period. */
export function PayTaxDialog({ open, period, duePeriods, accounts, eFile = false, simulated = false, onClose, onSaved }: PayTaxDialogProps) {
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
      if (eFile) {
        await taxService.fileReturn({
          agency_id: chosen.agency_id,
          period_start: chosen.period_start,
          period_end: chosen.period_end,
          payment_date: paymentDate,
          payment_account_id: Number(accountId),
        });
        onSaved();
        return;
      }
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
    <Modal title={eFile ? "File sales tax return" : "Record sales tax payment"} open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        {eFile && (
          <p className="text-sm text-gray-600">
            The return is filed electronically for the full balance of the period, and the payment is recorded.
            {simulated && <SimulatedBadge title="Simulated: nothing is really filed; you get a made-up confirmation number." />}
          </p>
        )}
        <Field label="Filing period" required>
          <Select required value={chosenKey} onChange={(e) => choosePeriod(e.target.value)} placeholder="Choose a period" options={periodOptions} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Payment amount" required>
            <TextInput type="number" step="0.01" min="0.01" required readOnly={eFile} value={eFile && chosen ? chosen.balance : amount} onChange={(e) => setAmount(e.target.value)} />
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
        {!eFile && (
          <Field label="Memo">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : eFile ? "File return and pay" : "Record payment"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
