"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate, formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, inventoryService, productService } from "@/services";
import { Account, InventoryAdjustment, Product } from "@/types/models";

interface LineState {
  productId: string;
  /** The quantity the user counted. */
  newQuantity: string;
}

interface AdjustmentFormProps {
  items: Product[];
  accounts: Account[];
  onSaved: () => void;
  onCancel: () => void;
}

/** "Inventory qty adjustment": type the new quantity, the change is worked out. */
function AdjustmentForm({ items, accounts, onSaved, onCancel }: AdjustmentFormProps) {
  const [adjustmentDate, setAdjustmentDate] = useState(todayString());
  const [accountId, setAccountId] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<LineState[]>([{ productId: "", newQuantity: "" }]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function onHand(productId: string): number {
    const item = items.find((product) => product.id === Number(productId));
    return item ? toNumber(item.quantity_on_hand) : 0;
  }

  function change(line: LineState): number {
    if (!line.productId || line.newQuantity === "") {
      return 0;
    }
    return Math.round((toNumber(line.newQuantity) - onHand(line.productId)) * 100) / 100;
  }

  function updateLine(index: number, changes: Partial<LineState>) {
    setLines(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await inventoryService.createAdjustment({
        adjustment_date: adjustmentDate,
        account_id: accountId ? Number(accountId) : null,
        memo: memo,
        lines: lines.filter((line) => change(line) !== 0).map((line) => ({ product_id: Number(line.productId), quantity_change: String(change(line)) })),
      });
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the adjustment.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Adjustment date" required>
          <TextInput type="date" required value={adjustmentDate} onChange={(e) => setAdjustmentDate(e.target.value)} />
        </Field>
        <Field label="Inventory adjustment account">
          <Select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            placeholder="Inventory Shrinkage (default)"
            options={accounts.map((account) => ({ value: account.id, label: account.full_name }))}
          />
        </Field>
      </div>
      <table className="w-full text-sm">
        <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
          <tr>
            <th className="py-2">Item</th>
            <th className="w-24 py-2 text-right">On hand</th>
            <th className="w-28 py-2 pl-2">New qty</th>
            <th className="w-24 py-2 text-right">Change</th>
            <th className="w-8"></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index} className="border-b border-gray-100">
              <td className="py-2 pr-2">
                <Select
                  value={line.productId}
                  onChange={(e) => updateLine(index, { productId: e.target.value })}
                  placeholder="Choose an item"
                  options={items.map((item) => ({ value: item.id, label: item.name }))}
                />
              </td>
              <td className="py-2 text-right">{line.productId ? onHand(line.productId) : ""}</td>
              <td className="py-2 pl-2">
                <TextInput type="number" step="0.01" min="0" value={line.newQuantity} onChange={(e) => updateLine(index, { newQuantity: e.target.value })} />
              </td>
              <td className={"py-2 text-right font-medium " + (change(line) < 0 ? "text-red-600" : "")}>
                {change(line) > 0 ? "+" : ""}
                {change(line) || ""}
              </td>
              <td className="py-2 pl-2">
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
      <Button type="button" variant="ghost" onClick={() => setLines([...lines, { productId: "", newQuantity: "" }])}>
        <Plus size={16} /> Add line
      </Button>
      <Field label="Memo">
        <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="e.g. Year-end stock count" />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}

export default function InventoryAdjustmentsPage() {
  const { company } = useAuth();
  const adjustments = useLoad(() => inventoryService.adjustments());
  const products = useLoad(() => productService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [open, setOpen] = useState(false);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setOpen(true);
    }
  }, [openFromMenu]);

  if (products.loading || accounts.loading) {
    return <Loading />;
  }

  const allProducts = products.data || [];
  const items = allProducts.filter((product) => product.product_type === "INVENTORY" && product.is_active);
  const names: Record<number, string> = {};
  for (const product of allProducts) {
    names[product.id] = product.name;
  }

  function describe(adjustment: InventoryAdjustment): string {
    return adjustment.lines
      .map((line) => names[line.product_id] + " " + (toNumber(line.quantity_change) > 0 ? "+" : "") + toNumber(line.quantity_change))
      .join(", ");
  }

  function totalValue(adjustment: InventoryAdjustment): number {
    let total = 0;
    for (const line of adjustment.lines) {
      total += toNumber(line.value_change);
    }
    return total;
  }

  async function voidAdjustment(adjustment: InventoryAdjustment) {
    if (window.confirm("Void adjustment " + adjustment.adjustment_number + "? The quantities go back to how they were.")) {
      try {
        await inventoryService.voidAdjustment(adjustment.id);
        adjustments.reload();
        products.reload();
      } catch (problem) {
        window.alert(problem instanceof Error ? problem.message : "Could not void.");
      }
    }
  }

  function afterSave() {
    setOpen(false);
    adjustments.reload();
    products.reload();
  }

  return (
    <div>
      <PageHeader
        title="Inventory adjustments"
        subtitle="Correct quantities on hand after a stock count, damage or loss."
        actions={
          <Button onClick={() => setOpen(true)} disabled={items.length === 0}>
            <Plus size={16} /> New adjustment
          </Button>
        }
      />
      <ErrorMessage message={adjustments.error} />
      {items.length === 0 && <p className="mb-4 text-sm text-gray-600">Add an inventory item under Products & services first.</p>}
      <DataTable
        rows={adjustments.data || []}
        rowKey={(row) => row.id}
        emptyText="No adjustments yet."
        columns={[
          { header: "No.", render: (row) => row.adjustment_number },
          { header: "Date", render: (row) => formatDate(row.adjustment_date) },
          { header: "Items", render: (row) => describe(row) },
          { header: "Account", render: (row) => row.account.name },
          { header: "Memo", render: (row) => row.memo },
          {
            header: "Value",
            align: "right",
            render: (row) => (row.is_void ? <span className="text-gray-400">Void</span> : formatMoney(totalValue(row), company?.currency)),
          },
          {
            header: "Void",
            align: "right",
            render: (row) =>
              row.is_void ? null : (
                <button onClick={() => voidAdjustment(row)} className="text-sm text-gray-500 hover:text-red-600">
                  Void
                </button>
              ),
          },
        ]}
      />
      <Modal title="Inventory quantity adjustment" open={open} onClose={() => setOpen(false)} wide>
        {open && <AdjustmentForm items={items} accounts={accounts.data || []} onSaved={afterSave} onCancel={() => setOpen(false)} />}
      </Modal>
    </div>
  );
}
