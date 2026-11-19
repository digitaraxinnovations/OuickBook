"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { ProductInput } from "@/types/inputs";
import { Account, Product, ProductType } from "@/types/models";

function productToInput(product: Product | null): ProductInput {
  return {
    name: product?.name || "",
    sku: product?.sku || "",
    product_type: product?.product_type || "SERVICE",
    description: product?.description || "",
    sales_price: product?.sales_price || "0.00",
    income_account_id: product ? product.income_account.id : null,
    is_active: product ? product.is_active : true,
  };
}

interface ProductFormProps {
  initial: Product | null;
  incomeAccounts: Account[];
  onSave: (input: ProductInput) => Promise<void>;
  onCancel: () => void;
}

export function ProductForm({ initial, incomeAccounts, onSave, onCancel }: ProductFormProps) {
  const form = useFormState<ProductInput>(productToInput(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(form.values);
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
          <Select
            value={form.values.product_type}
            onChange={(e) => form.setField("product_type", e.target.value as ProductType)}
            options={[
              { value: "SERVICE", label: "Service" },
              { value: "NON_INVENTORY", label: "Non-inventory product" },
            ]}
          />
        </Field>
        <Field label="SKU">
          <TextInput value={form.values.sku} onChange={(e) => form.setField("sku", e.target.value)} />
        </Field>
      </div>
      <Field label="Name" required>
        <TextInput required value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} />
      </Field>
      <Field label="Description (shown on invoices)">
        <TextArea rows={2} value={form.values.description} onChange={(e) => form.setField("description", e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Sales price">
          <TextInput type="number" step="0.01" min="0" value={form.values.sales_price} onChange={(e) => form.setField("sales_price", e.target.value)} />
        </Field>
        <Field label="Income account">
          <Select
            value={form.values.income_account_id ?? ""}
            onChange={(e) => form.setField("income_account_id", e.target.value ? Number(e.target.value) : null)}
            placeholder="Sales (default)"
            options={incomeAccounts.map((account) => ({ value: account.id, label: account.name }))}
          />
        </Field>
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.values.is_active} onChange={(e) => form.setField("is_active", e.target.checked)} />
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
