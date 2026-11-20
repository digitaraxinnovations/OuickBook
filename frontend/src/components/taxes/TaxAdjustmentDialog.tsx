"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { todayString } from "@/lib/format";
import { taxService } from "@/services";
import { Account, TaxAgency } from "@/types/models";

interface TaxAdjustmentDialogProps {
  open: boolean;
  agencies: TaxAgency[];
  accounts: Account[];
  onClose: () => void;
  onSaved: () => void;
}

/** Increase or decrease what you owe an agency (e.g. a discount for filing early). */
export function TaxAdjustmentDialog({ open, agencies, accounts, onClose, onSaved }: TaxAdjustmentDialogProps) {
  const [agencyId, setAgencyId] = useState(agencies.length === 1 ? String(agencies[0].id) : "");
  const [direction, setDirection] = useState("DECREASE");
  const [amount, setAmount] = useState("");
  const [adjustmentDate, setAdjustmentDate] = useState(todayString());
  const [accountId, setAccountId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // The other side is usually an income account (discounts) or an expense account (penalties).
  const accountOptions = accounts
    .filter((account) => account.account_type === "INCOME" || account.account_type === "EXPENSE")
    .map((account) => ({ value: account.id, label: account.full_name }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const signedAmount = direction === "DECREASE" ? "-" + amount : amount;
    try {
      await taxService.recordAdjustment({
        agency_id: Number(agencyId),
        adjustment_date: adjustmentDate,
        amount: signedAmount,
        account_id: Number(accountId),
        reason: reason,
      });
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the adjustment.");
      setSaving(false);
    }
  }

  return (
    <Modal title="Sales tax adjustment" open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Tax agency" required>
            <Select
              required
              value={agencyId}
              onChange={(e) => setAgencyId(e.target.value)}
              placeholder="Choose"
              options={agencies.map((agency) => ({ value: agency.id, label: agency.name }))}
            />
          </Field>
          <Field label="Adjustment date" required>
            <TextInput type="date" required value={adjustmentDate} onChange={(e) => setAdjustmentDate(e.target.value)} />
          </Field>
          <Field label="Type" required>
            <Select
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
              options={[
                { value: "DECREASE", label: "Decrease (you owe less)" },
                { value: "INCREASE", label: "Increase (you owe more)" },
              ]}
            />
          </Field>
          <Field label="Amount" required>
            <TextInput type="number" step="0.01" min="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
          </Field>
        </div>
        <Field label="Adjustment account" required>
          <Select required value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="e.g. Other Income" options={accountOptions} />
        </Field>
        <Field label="Reason" required>
          <TextInput required value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Discount for filing early" />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
