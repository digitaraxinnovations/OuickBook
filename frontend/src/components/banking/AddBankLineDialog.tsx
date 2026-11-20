"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { bankingService } from "@/services";
import { BankTransaction } from "@/types/models";

interface LineState {
  account_id: string;
  amount: string;
  description: string;
}

interface AddBankLineDialogProps {
  transaction: BankTransaction;
  categoryOptions: SelectOption[];
  vendorOptions: SelectOption[];
  currency?: string;
  onClose: () => void;
  onDone: () => void;
}

/**
 * Categorize one bank line. One row = a simple add; more rows = a split.
 * Choosing another bank or card account makes it a transfer.
 */
export function AddBankLineDialog({ transaction, categoryOptions, vendorOptions, currency, onClose, onDone }: AddBankLineDialogProps) {
  const total = Math.abs(toNumber(transaction.amount));
  const [vendorId, setVendorId] = useState(transaction.suggested_vendor_id ? String(transaction.suggested_vendor_id) : "");
  const [memo, setMemo] = useState(transaction.description);
  const [lines, setLines] = useState<LineState[]>([
    { account_id: transaction.suggested_account ? String(transaction.suggested_account.id) : "", amount: total.toFixed(2), description: "" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  let used = 0;
  for (const line of lines) {
    used += toNumber(line.amount);
  }
  const left = Math.round((total - used) * 100) / 100;

  function updateLine(index: number, changes: Partial<LineState>) {
    setLines(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await bankingService.add(transaction.id, {
        vendor_id: vendorId ? Number(vendorId) : null,
        memo: memo,
        lines: lines.map((line) => ({ account_id: Number(line.account_id), amount: line.amount, description: line.description })),
      });
      onDone();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not add.");
      setSaving(false);
    }
  }

  const moneyIn = toNumber(transaction.amount) > 0;

  return (
    <Modal title={(moneyIn ? "Money in: " : "Money out: ") + formatMoney(total, currency)} open onClose={onClose} wide>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <p className="text-sm text-gray-600">
          {formatDate(transaction.txn_date)} · {transaction.description}
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label={moneyIn ? "Received from (vendor)" : "Payee"}>
            <Select value={vendorId} onChange={(e) => setVendorId(e.target.value)} placeholder="(none)" options={vendorOptions} />
          </Field>
          <Field label="Memo">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
        </div>
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Category (or bank/card account for a transfer)</th>
              <th className="py-2">Description</th>
              <th className="w-32 py-2">Amount</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100">
                <td className="py-2 pr-2">
                  <Select required value={line.account_id} onChange={(e) => updateLine(index, { account_id: e.target.value })} placeholder="Choose" options={categoryOptions} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" min="0.01" required value={line.amount} onChange={(e) => updateLine(index, { amount: e.target.value })} />
                </td>
                <td>
                  {lines.length > 1 && (
                    <button type="button" onClick={() => setLines(lines.filter((_, i) => i !== index))} className="text-gray-400 hover:text-red-600" aria-label="Remove line">
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={() => setLines([...lines, { account_id: "", amount: left > 0 ? left.toFixed(2) : "", description: "" }])}
          >
            <Plus size={16} /> Split
          </Button>
          <span className={"text-sm " + (left === 0 ? "text-gray-500" : "font-semibold text-red-600")}>
            {left === 0 ? "Fully assigned" : "Left to assign: " + formatMoney(left, currency)}
          </span>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || left !== 0}>
            {saving ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
