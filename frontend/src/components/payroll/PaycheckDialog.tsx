"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { payItemKindLabels } from "@/config/payroll.config";
import { payrollService } from "@/services";
import { Paycheck, PayItem, PayrollRun } from "@/types/models";

interface ItemRow {
  payItemId: number;
  amount: string;
}

/** The pay item lines already on the paycheck (regular/overtime/salary are worked out from hours). */
function itemRows(paycheck: Paycheck): ItemRow[] {
  const rows: ItemRow[] = [];
  for (const line of paycheck.lines) {
    if (line.pay_item_id !== null) {
      rows.push({ payItemId: line.pay_item_id, amount: line.amount });
    }
  }
  return rows;
}

interface PaycheckDialogProps {
  runId: number;
  paycheck: Paycheck;
  payItems: PayItem[];
  onClose: () => void;
  onSaved: (run: PayrollRun) => void;
}

/** Change hours and amounts on one paycheck of a draft payroll. */
export function PaycheckDialog({ runId, paycheck, payItems, onClose, onSaved }: PaycheckDialogProps) {
  const isHourly = paycheck.employee.pay_type === "HOURLY";
  const [regularHours, setRegularHours] = useState(paycheck.regular_hours);
  const [overtimeHours, setOvertimeHours] = useState(paycheck.overtime_hours);
  const [rows, setRows] = useState<ItemRow[]>(itemRows(paycheck));
  // Until an amount is typed by hand, the usual items are worked out again (so percentages follow the hours).
  const [amountsTyped, setAmountsTyped] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function updateRow(index: number, changes: Partial<ItemRow>) {
    setRows(rows.map((row, i) => (i === index ? { ...row, ...changes } : row)));
    setAmountsTyped(true);
  }

  function removeRow(index: number) {
    setRows(rows.filter((_, i) => i !== index));
    setAmountsTyped(true);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const run = await payrollService.updatePaycheck(runId, paycheck.id, {
        regular_hours: regularHours || "0",
        overtime_hours: overtimeHours || "0",
        items: rows.filter((row) => row.payItemId).map((row) => ({ pay_item_id: row.payItemId, amount: row.amount || "0" })),
        use_usual_items: !amountsTyped,
      });
      onSaved(run);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the paycheck.");
      setSaving(false);
    }
  }

  return (
    <Modal title={"Paycheck - " + paycheck.employee.display_name} open={true} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        {isHourly ? (
          <div className="grid grid-cols-2 gap-4">
            <Field label="Regular hours">
              <TextInput type="number" step="0.01" min="0" value={regularHours} onChange={(e) => setRegularHours(e.target.value)} />
            </Field>
            <Field label="Overtime hours">
              <TextInput type="number" step="0.01" min="0" value={overtimeHours} onChange={(e) => setOvertimeHours(e.target.value)} />
            </Field>
          </div>
        ) : (
          <p className="text-sm text-gray-600">Salary is split evenly over the pay periods of the year.</p>
        )}
        <div>
          <div className="mb-2 text-sm font-medium text-gray-700">Earnings, deductions and taxes (amounts for this paycheck)</div>
          {rows.map((row, index) => (
            <div key={index} className="mb-2 flex items-center gap-2">
              <Select
                value={row.payItemId || ""}
                onChange={(e) => updateRow(index, { payItemId: Number(e.target.value) })}
                placeholder="Choose a pay item"
                options={payItems.map((item) => ({ value: item.id, label: item.name + " (" + payItemKindLabels[item.kind] + ")" }))}
              />
              <TextInput
                className="w-28!"
                type="number"
                step="0.01"
                min="0"
                value={row.amount}
                onChange={(e) => updateRow(index, { amount: e.target.value })}
                aria-label="Amount"
              />
              <button type="button" onClick={() => removeRow(index)} className="text-gray-400 hover:text-red-600" aria-label="Remove">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          <div className="flex items-center justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setRows([...rows, { payItemId: 0, amount: "" }]);
                setAmountsTyped(true);
              }}
            >
              <Plus size={16} /> Add pay item
            </Button>
            <span className="text-xs text-gray-500">
              {amountsTyped ? "Amounts as typed." : "Usual amounts are worked out again from the new gross pay."}
            </span>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save paycheck"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
