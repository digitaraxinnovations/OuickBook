"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";

export interface JournalLineState {
  account_id: string;
  description: string;
  debit: string;
  credit: string;
}

export function emptyJournalLine(): JournalLineState {
  return { account_id: "", description: "", debit: "", credit: "" };
}

export function journalTotals(lines: JournalLineState[]) {
  let debit = 0;
  let credit = 0;
  for (const line of lines) {
    debit += toNumber(line.debit);
    credit += toNumber(line.credit);
  }
  const difference = debit - credit;
  return { debit, credit, difference, isBalanced: Math.abs(difference) < 0.005 && debit > 0 };
}

/** Turns the editor rows into what the API expects. */
export function journalLinesToInput(lines: JournalLineState[]) {
  return lines.map((line) => ({
    account_id: Number(line.account_id),
    description: line.description,
    debit: line.debit || "0",
    credit: line.credit || "0",
  }));
}

interface JournalLinesEditorProps {
  lines: JournalLineState[];
  onChange: (lines: JournalLineState[]) => void;
  accountOptions: SelectOption[];
  currency?: string;
}

/** Debit / credit rows used by journal entries and recurring journal entries. */
export function JournalLinesEditor({ lines, onChange, accountOptions, currency }: JournalLinesEditorProps) {
  const totals = journalTotals(lines);

  function updateLine(index: number, changes: Partial<JournalLineState>) {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="w-8 py-2">#</th>
              <th className="w-64 py-2">Account</th>
              <th className="w-36 py-2">Debit</th>
              <th className="w-36 py-2">Credit</th>
              <th className="py-2">Description</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100">
                <td className="py-2 text-gray-500">{index + 1}</td>
                <td className="py-2 pr-2">
                  <Select required value={line.account_id} onChange={(e) => updateLine(index, { account_id: e.target.value })} placeholder="Choose an account" options={accountOptions} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" min="0" value={line.debit} onChange={(e) => updateLine(index, { debit: e.target.value, credit: "" })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" min="0" value={line.credit} onChange={(e) => updateLine(index, { credit: e.target.value, debit: "" })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                </td>
                <td className="py-2">
                  {lines.length > 2 && (
                    <button type="button" onClick={() => onChange(lines.filter((_, i) => i !== index))} className="text-gray-400 hover:text-red-600" aria-label="Remove line">
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            <tr className="font-semibold">
              <td></td>
              <td className="py-3 pr-4 text-right">Total</td>
              <td className="py-3">{formatMoney(totals.debit, currency)}</td>
              <td className="py-3">{formatMoney(totals.credit, currency)}</td>
              <td className="py-3">
                {!totals.isBalanced && totals.debit + totals.credit > 0 && (
                  <span className="text-red-600">Out of balance by {formatMoney(Math.abs(totals.difference), currency)}</span>
                )}
              </td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
      <Button type="button" variant="ghost" className="mt-3" onClick={() => onChange([...lines, emptyJournalLine()])}>
        <Plus size={16} /> Add line
      </Button>
    </div>
  );
}
