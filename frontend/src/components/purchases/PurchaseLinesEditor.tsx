"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";
import { PurchaseLineInput } from "@/types/inputs";

export function emptyPurchaseLine(): PurchaseLineInput {
  return { account_id: 0, description: "", quantity: "1", rate: "", customer_id: null };
}

export function purchaseLineAmount(line: PurchaseLineInput): number {
  return toNumber(line.quantity) * toNumber(line.rate);
}

export function purchaseLinesTotal(lines: PurchaseLineInput[]): number {
  let total = 0;
  for (const line of lines) {
    total += purchaseLineAmount(line);
  }
  return total;
}

interface PurchaseLinesEditorProps {
  lines: PurchaseLineInput[];
  onChange: (lines: PurchaseLineInput[]) => void;
  categoryOptions: SelectOption[];
  customerOptions: SelectOption[];
  currency?: string;
}

/** Category rows used by bills, vendor credits and purchase orders. */
export function PurchaseLinesEditor({ lines, onChange, categoryOptions, customerOptions, currency }: PurchaseLinesEditorProps) {
  function updateLine(index: number, changes: Partial<PurchaseLineInput>) {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="w-8 py-2">#</th>
              <th className="w-56 py-2">Category</th>
              <th className="py-2">Description</th>
              <th className="w-20 py-2">Qty</th>
              <th className="w-28 py-2">Rate</th>
              <th className="w-28 py-2 text-right">Amount</th>
              <th className="w-44 py-2 pl-2">Billable to</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100 align-top">
                <td className="py-2 text-gray-500">{index + 1}</td>
                <td className="py-2 pr-2">
                  <Select
                    required
                    value={line.account_id || ""}
                    onChange={(e) => updateLine(index, { account_id: Number(e.target.value) })}
                    placeholder="Choose a category"
                    options={categoryOptions}
                  />
                </td>
                <td className="py-2 pr-2">
                  <TextInput value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" min="0.01" required value={line.quantity} onChange={(e) => updateLine(index, { quantity: e.target.value })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" required value={line.rate} onChange={(e) => updateLine(index, { rate: e.target.value })} />
                </td>
                <td className="py-2 pt-4 text-right font-medium">{formatMoney(purchaseLineAmount(line), currency)}</td>
                <td className="py-2 pl-2">
                  <Select
                    value={line.customer_id ?? ""}
                    onChange={(e) => updateLine(index, { customer_id: e.target.value ? Number(e.target.value) : null })}
                    placeholder="-"
                    options={customerOptions}
                  />
                </td>
                <td className="py-2 pl-2">
                  {lines.length > 1 && (
                    <button type="button" onClick={() => onChange(lines.filter((_, i) => i !== index))} className="mt-2 text-gray-400 hover:text-red-600" aria-label="Remove line">
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Button type="button" variant="ghost" className="mt-3" onClick={() => onChange([...lines, emptyPurchaseLine()])}>
        <Plus size={16} /> Add line
      </Button>
    </div>
  );
}
