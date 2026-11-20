"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { formatMoney, todayString, toNumber } from "@/lib/format";
import { ProductInput } from "@/types/inputs";
import { Account, Product, ProductCategory, ProductType } from "@/types/models";

const TYPE_OPTIONS = [
  { value: "SERVICE", label: "Service" },
  { value: "NON_INVENTORY", label: "Non-inventory product" },
  { value: "INVENTORY", label: "Inventory item (track quantity)" },
  { value: "BUNDLE", label: "Bundle (items sold together)" },
];

function productToInput(product: Product | null): ProductInput {
  return {
    name: product?.name || "",
    sku: product?.sku || "",
    product_type: product?.product_type || "SERVICE",
    description: product?.description || "",
    sales_price: product?.sales_price || "0.00",
    income_account_id: product ? product.income_account.id : null,
    is_active: product ? product.is_active : true,
    taxable: product ? product.taxable : true,
    category_id: product?.category ? product.category.id : null,
    purchase_description: product?.purchase_description || "",
    purchase_cost: product?.purchase_cost || "0.00",
    expense_account_id: product?.expense_account_id ?? null,
    inventory_asset_account_id: product?.inventory_asset_account_id ?? null,
    cogs_account_id: product?.cogs_account_id ?? null,
    reorder_point: product?.reorder_point ?? null,
    initial_quantity: "0",
    as_of_date: todayString(),
    components: product ? product.components.map((item) => ({ product_id: item.product_id, quantity: item.quantity })) : [],
  };
}

function accountOptions(accounts: Account[], type: string) {
  return accounts.filter((account) => account.account_type === type).map((account) => ({ value: account.id, label: account.full_name }));
}

interface ProductFormProps {
  initial: Product | null;
  accounts: Account[];
  categories: ProductCategory[];
  /** Items that can go into a bundle. */
  products: Product[];
  currency?: string;
  onSave: (input: ProductInput) => Promise<void>;
  onCancel: () => void;
}

export function ProductForm({ initial, accounts, categories, products, currency, onSave, onCancel }: ProductFormProps) {
  const form = useFormState<ProductInput>(productToInput(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const values = form.values;
  const isInventory = values.product_type === "INVENTORY";
  const isBundle = values.product_type === "BUNDLE";

  const bundleChoices = products.filter((item) => item.product_type !== "BUNDLE" && item.id !== initial?.id);
  let bundlePrice = 0;
  for (const component of values.components) {
    const item = products.find((product) => product.id === component.product_id);
    if (item) {
      bundlePrice += toNumber(item.sales_price) * toNumber(component.quantity);
    }
  }

  function setComponent(index: number, changes: Partial<{ product_id: number; quantity: string }>) {
    form.setField(
      "components",
      values.components.map((component, i) => (i === index ? { ...component, ...changes } : component)),
    );
  }

  function addComponent() {
    form.setField("components", [...values.components, { product_id: 0, quantity: "1" }]);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave({ ...values, components: values.components.filter((component) => component.product_id) });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Type" required>
          <Select value={values.product_type} onChange={(e) => form.setField("product_type", e.target.value as ProductType)} options={TYPE_OPTIONS} />
        </Field>
        <Field label="SKU">
          <TextInput value={values.sku} onChange={(e) => form.setField("sku", e.target.value)} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name" required>
          <TextInput required value={values.name} onChange={(e) => form.setField("name", e.target.value)} />
        </Field>
        <Field label="Category">
          <Select
            value={values.category_id ?? ""}
            onChange={(e) => form.setField("category_id", e.target.value ? Number(e.target.value) : null)}
            placeholder="None"
            options={categories.map((category) => ({ value: category.id, label: category.name }))}
          />
        </Field>
      </div>

      {isInventory && (
        <div className="grid grid-cols-3 gap-4 rounded-md bg-gray-50 p-3">
          {initial ? (
            <div>
              <div className="text-xs font-medium text-gray-600">Quantity on hand</div>
              <div className="mt-2 text-lg font-semibold">{toNumber(initial.quantity_on_hand)}</div>
              <div className="text-xs text-gray-500">Change it with an inventory adjustment.</div>
            </div>
          ) : (
            <Field label="Starting quantity">
              <TextInput type="number" step="0.01" min="0" value={values.initial_quantity} onChange={(e) => form.setField("initial_quantity", e.target.value)} />
            </Field>
          )}
          {!initial && (
            <Field label="As of date">
              <TextInput type="date" value={values.as_of_date || ""} onChange={(e) => form.setField("as_of_date", e.target.value)} />
            </Field>
          )}
          <Field label="Reorder point">
            <TextInput
              type="number"
              step="0.01"
              min="0"
              value={values.reorder_point ?? ""}
              onChange={(e) => form.setField("reorder_point", e.target.value || null)}
              placeholder="No alert"
            />
          </Field>
        </div>
      )}

      {isBundle && (
        <div className="rounded-md border border-gray-200 p-3">
          <div className="mb-2 text-sm font-medium text-gray-700">Items in the bundle</div>
          {values.components.map((component, index) => (
            <div key={index} className="mb-2 flex items-center gap-2">
              <Select
                value={component.product_id || ""}
                onChange={(e) => setComponent(index, { product_id: Number(e.target.value) })}
                placeholder="Choose an item"
                options={bundleChoices.map((item) => ({ value: item.id, label: item.name }))}
              />
              <TextInput
                className="w-24!"
                type="number"
                step="0.01"
                min="0.01"
                value={component.quantity}
                onChange={(e) => setComponent(index, { quantity: e.target.value })}
                aria-label="Quantity"
              />
              <button
                type="button"
                onClick={() => form.setField("components", values.components.filter((_, i) => i !== index))}
                className="text-gray-400 hover:text-red-600"
                aria-label="Remove item"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          <div className="flex items-center justify-between">
            <Button type="button" variant="ghost" onClick={addComponent}>
              <Plus size={16} /> Add item
            </Button>
            <span className="text-sm">
              Bundle price: <strong>{formatMoney(bundlePrice, currency)}</strong>
            </span>
          </div>
        </div>
      )}

      <h3 className="pt-2 text-xs font-semibold uppercase text-gray-500">Sales</h3>
      <Field label="Description (shown on invoices)">
        <TextArea rows={2} value={values.description} onChange={(e) => form.setField("description", e.target.value)} />
      </Field>
      {!isBundle && (
        <div className="grid grid-cols-2 gap-4">
          <Field label="Sales price">
            <TextInput type="number" step="0.01" min="0" value={values.sales_price} onChange={(e) => form.setField("sales_price", e.target.value)} />
          </Field>
          <Field label="Income account">
            <Select
              value={values.income_account_id ?? ""}
              onChange={(e) => form.setField("income_account_id", e.target.value ? Number(e.target.value) : null)}
              placeholder="Sales (default)"
              options={accountOptions(accounts, "INCOME")}
            />
          </Field>
        </div>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={values.taxable} onChange={(e) => form.setField("taxable", e.target.checked)} />
        Charge sales tax on this item
      </label>

      {!isBundle && (
        <>
          <h3 className="pt-2 text-xs font-semibold uppercase text-gray-500">Purchasing</h3>
          <Field label="Purchase description (shown on bills)">
            <TextInput value={values.purchase_description} onChange={(e) => form.setField("purchase_description", e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Cost">
              <TextInput type="number" step="0.01" min="0" value={values.purchase_cost} onChange={(e) => form.setField("purchase_cost", e.target.value)} />
            </Field>
            {isInventory ? (
              <Field label="Inventory asset account">
                <Select
                  value={values.inventory_asset_account_id ?? ""}
                  onChange={(e) => form.setField("inventory_asset_account_id", e.target.value ? Number(e.target.value) : null)}
                  placeholder="Inventory Asset (default)"
                  options={accountOptions(accounts, "ASSET")}
                />
              </Field>
            ) : (
              <Field label="Expense account">
                <Select
                  value={values.expense_account_id ?? ""}
                  onChange={(e) => form.setField("expense_account_id", e.target.value ? Number(e.target.value) : null)}
                  placeholder="Choose when buying"
                  options={accountOptions(accounts, "EXPENSE")}
                />
              </Field>
            )}
          </div>
          {isInventory && (
            <Field label="Cost of goods sold account">
              <Select
                value={values.cogs_account_id ?? ""}
                onChange={(e) => form.setField("cogs_account_id", e.target.value ? Number(e.target.value) : null)}
                placeholder="Cost of Goods Sold (default)"
                options={accountOptions(accounts, "EXPENSE")}
              />
            </Field>
          )}
        </>
      )}

      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={values.is_active} onChange={(e) => form.setField("is_active", e.target.checked)} />
          Active
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
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
