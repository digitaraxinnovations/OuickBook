"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";
import { PurchaseLineInput } from "@/types/inputs";
import { Product } from "@/types/models";

export function emptyPurchaseLine(): PurchaseLineInput {
  return { account_id: null, product_id: null, description: "", quantity: "1", rate: "", customer_id: null };
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

/** Products that can be bought (bundles are bought as their items). */
export function purchasableProducts(products: Product[]): Product[] {
  return products.filter((product) => product.product_type !== "BUNDLE");
}

interface PurchaseLinesEditorProps {
  lines: PurchaseLineInput[];
  onChange: (lines: PurchaseLineInput[]) => void;
  categoryOptions: SelectOption[];
  customerOptions: SelectOption[];
  /** When given, each line can be an item (product or service) instead of a category. */
  products?: Product[];
  currency?: string;
}

/** Category or item rows used by bills, vendor credits and purchase orders. */
export function PurchaseLinesEditor({ lines, onChange, categoryOptions, customerOptions, products, currency }: PurchaseLinesEditorProps) {
  const items = products ? purchasableProducts(products) : [];
  const productOptions = items.map((product) => ({ value: product.id, label: product.name }));

  function updateLine(index: number, changes: Partial<PurchaseLineInput>) {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  /** Picking an item fills in its purchase description, cost and expense account. */
  function chooseProduct(index: number, productId: string) {
    const product = items.find((item) => item.id === Number(productId));
    if (!product) {
      updateLine(index, { product_id: null });
      return;
    }
    updateLine(index, {
      product_id: product.id,
      description: product.purchase_description || product.name,
      rate: product.purchase_cost,
      account_id: product.product_type === "INVENTORY" ? null : product.expense_account_id,
    });
  }

  function isInventoryLine(line: PurchaseLineInput): boolean {
    const product = items.find((item) => item.id === line.product_id);
    return product !== undefined && product.product_type === "INVENTORY";
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="w-8 py-2">#</th>
              {products && <th className="w-44 py-2">Product / service</th>}
              <th className="w-48 py-2">Category</th>
              <th className="py-2">Description</th>
              <th className="w-20 py-2">Qty</th>
              <th className="w-28 py-2">Rate</th>
              <th className="w-28 py-2 text-right">Amount</th>
              <th className="w-40 py-2 pl-2">Billable to</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100 align-top">
                <td className="py-2 text-gray-500">{index + 1}</td>
                {products && (
                  <td className="py-2 pr-2">
                    <Select value={line.product_id ?? ""} onChange={(e) => chooseProduct(index, e.target.value)} placeholder="-" options={productOptions} />
                  </td>
                )}
                <td className="py-2 pr-2">
                  {isInventoryLine(line) ? (
                    <div className="pt-2 text-gray-500">Inventory Asset</div>
                  ) : (
                    <Select
                      required={line.product_id === null}
                      value={line.account_id ?? ""}
                      onChange={(e) => updateLine(index, { account_id: e.target.value ? Number(e.target.value) : null })}
                      placeholder={line.product_id ? "Item's account" : "Choose a category"}
                      options={categoryOptions}
                    />
                  )}
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
