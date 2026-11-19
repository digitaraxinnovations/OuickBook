"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";
import { SalesLineInput } from "@/types/inputs";
import { Product } from "@/types/models";

export function emptySalesLine(): SalesLineInput {
  return { product_id: null, description: "", quantity: "1", rate: "" };
}

export function salesLineAmount(line: SalesLineInput): number {
  return toNumber(line.quantity) * toNumber(line.rate);
}

interface SalesLinesEditorProps {
  lines: SalesLineInput[];
  onChange: (lines: SalesLineInput[]) => void;
  products: Product[];
  currency?: string;
}

/** Product / service rows used by invoices, estimates, receipts and credits. */
export function SalesLinesEditor({ lines, onChange, products, currency }: SalesLinesEditorProps) {
  const productOptions = products.map((product) => ({ value: product.id, label: product.name }));

  function updateLine(index: number, changes: Partial<SalesLineInput>) {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  /** Picking a product fills in its description and price. */
  function chooseProduct(index: number, productId: string) {
    if (!productId) {
      updateLine(index, { product_id: null });
      return;
    }
    const product = products.find((item) => item.id === Number(productId));
    if (product) {
      updateLine(index, { product_id: product.id, description: product.description || product.name, rate: product.sales_price });
    }
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="w-8 py-2">#</th>
              <th className="w-56 py-2">Product / service</th>
              <th className="py-2">Description</th>
              <th className="w-24 py-2">Qty</th>
              <th className="w-32 py-2">Rate</th>
              <th className="w-32 py-2 text-right">Amount</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100 align-top">
                <td className="py-2 text-gray-500">{index + 1}</td>
                <td className="py-2 pr-2">
                  <Select value={line.product_id ?? ""} onChange={(e) => chooseProduct(index, e.target.value)} placeholder="-" options={productOptions} />
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
                <td className="py-2 pt-4 text-right font-medium">{formatMoney(salesLineAmount(line), currency)}</td>
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
      <Button type="button" variant="ghost" className="mt-3" onClick={() => onChange([...lines, emptySalesLine()])}>
        <Plus size={16} /> Add line
      </Button>
    </div>
  );
}
