"use client";

import { Plus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, toNumber } from "@/lib/format";
import { customerService, inventoryService, productService } from "@/services";
import { Customer, PriceRule, Product, ProductCategory } from "@/types/models";

// ---------- category form ----------

function CategoryForm({ initial, categories, onSaved, onCancel }: {
  initial: ProductCategory | null;
  categories: ProductCategory[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [parentId, setParentId] = useState(initial && initial.parent_id ? String(initial.parent_id) : "");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await inventoryService.saveCategory({ name: name, parent_id: parentId ? Number(parentId) : null }, initial?.id);
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <Field label="Name" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Inside category">
        <Select
          value={parentId}
          onChange={(e) => setParentId(e.target.value)}
          placeholder="(top level)"
          options={categories.filter((category) => category.id !== initial?.id).map((category) => ({ value: category.id, label: category.name }))}
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}

// ---------- price rule form ----------

interface RuleFormProps {
  initial: PriceRule | null;
  categories: ProductCategory[];
  products: Product[];
  customers: Customer[];
  onSaved: () => void;
  onCancel: () => void;
}

function RuleForm({ initial, categories, products, customers, onSaved, onCancel }: RuleFormProps) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [direction, setDirection] = useState(initial && toNumber(initial.adjustment_percent) > 0 ? "UP" : "DOWN");
  const [percent, setPercent] = useState(initial ? String(Math.abs(toNumber(initial.adjustment_percent))) : "");
  const [scope, setScope] = useState(initial?.product_id ? "PRODUCT" : initial?.category_id ? "CATEGORY" : "ALL");
  const [targetId, setTargetId] = useState(String(initial?.product_id || initial?.category_id || ""));
  const [customerId, setCustomerId] = useState(initial?.customer_id ? String(initial.customer_id) : "");
  const [startDate, setStartDate] = useState(initial?.start_date || "");
  const [endDate, setEndDate] = useState(initial?.end_date || "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const signed = direction === "DOWN" ? "-" + percent : percent;
    try {
      await inventoryService.savePriceRule(
        {
          name: name,
          adjustment_percent: signed,
          customer_id: customerId ? Number(customerId) : null,
          category_id: scope === "CATEGORY" && targetId ? Number(targetId) : null,
          product_id: scope === "PRODUCT" && targetId ? Number(targetId) : null,
          start_date: startDate || null,
          end_date: endDate || null,
          is_active: isActive,
        },
        initial?.id,
      );
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  const targetOptions =
    scope === "CATEGORY"
      ? categories.map((category) => ({ value: category.id, label: category.name }))
      : products.map((product) => ({ value: product.id, label: product.name }));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <Field label="Rule name" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Spring sale" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Change prices" required>
          <Select
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            options={[
              { value: "DOWN", label: "Lower by" },
              { value: "UP", label: "Raise by" },
            ]}
          />
        </Field>
        <Field label="Percent" required>
          <TextInput type="number" step="0.01" min="0.01" required value={percent} onChange={(e) => setPercent(e.target.value)} />
        </Field>
        <Field label="Applies to">
          <Select
            value={scope}
            onChange={(e) => {
              setScope(e.target.value);
              setTargetId("");
            }}
            options={[
              { value: "ALL", label: "All items" },
              { value: "CATEGORY", label: "One category" },
              { value: "PRODUCT", label: "One item" },
            ]}
          />
        </Field>
        {scope !== "ALL" ? (
          <Field label={scope === "CATEGORY" ? "Category" : "Item"} required>
            <Select required value={targetId} onChange={(e) => setTargetId(e.target.value)} placeholder="Choose" options={targetOptions} />
          </Field>
        ) : (
          <div />
        )}
        <Field label="Customer">
          <Select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="All customers"
            options={customers.map((customer) => ({ value: customer.id, label: customer.display_name }))}
          />
        </Field>
        <div />
        <Field label="Start date">
          <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="End date">
          <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}

// ---------- page ----------

type Editing = { kind: "category"; record: ProductCategory | null } | { kind: "rule"; record: PriceRule | null } | null;

export default function PriceRulesPage() {
  const categories = useLoad(() => inventoryService.categories());
  const rules = useLoad(() => inventoryService.priceRules());
  const products = useLoad(() => productService.list({ active_only: true }));
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const [editing, setEditing] = useState<Editing>(null);

  if (categories.loading || rules.loading || products.loading || customers.loading) {
    return <Loading />;
  }

  const categoryList = categories.data || [];
  const categoryNames: Record<number, string> = {};
  for (const category of categoryList) {
    categoryNames[category.id] = category.name;
  }
  const productNames: Record<number, string> = {};
  for (const product of products.data || []) {
    productNames[product.id] = product.name;
  }
  const customerNames: Record<number, string> = {};
  for (const customer of customers.data || []) {
    customerNames[customer.id] = customer.display_name;
  }

  function appliesTo(rule: PriceRule): string {
    if (rule.product_id) {
      return productNames[rule.product_id] || "Item";
    }
    if (rule.category_id) {
      return "Category: " + categoryNames[rule.category_id];
    }
    return "All items";
  }

  function dates(rule: PriceRule): string {
    if (!rule.start_date && !rule.end_date) {
      return "Always";
    }
    return (rule.start_date ? formatDate(rule.start_date) : "...") + " - " + (rule.end_date ? formatDate(rule.end_date) : "...");
  }

  function afterSave() {
    setEditing(null);
    categories.reload();
    rules.reload();
  }

  return (
    <div>
      <PageHeader title="Categories and price rules" subtitle="Group your items, and change prices for a sale or for special customers." />
      <ErrorMessage message={categories.error || rules.error} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          title="Categories"
          action={
            <Button variant="ghost" onClick={() => setEditing({ kind: "category", record: null })}>
              <Plus size={16} /> Add
            </Button>
          }
        >
          <DataTable
            rows={categoryList}
            rowKey={(row) => row.id}
            emptyText="No categories yet."
            onRowClick={(row) => setEditing({ kind: "category", record: row })}
            columns={[
              { header: "Name", render: (row) => row.name },
              { header: "Inside", render: (row) => (row.parent_id ? categoryNames[row.parent_id] : "") },
            ]}
          />
        </Card>
        <div className="lg:col-span-2">
          <Card
            title="Price rules"
            action={
              <Button variant="ghost" onClick={() => setEditing({ kind: "rule", record: null })}>
                <Plus size={16} /> Add rule
              </Button>
            }
          >
            <p className="mb-3 text-sm text-gray-600">
              Rule prices fill in automatically when you pick an item on a sales form. An item rule beats a category rule, which beats an
              all-items rule.
            </p>
            <DataTable
              rows={rules.data || []}
              rowKey={(row) => row.id}
              emptyText="No price rules yet."
              onRowClick={(row) => setEditing({ kind: "rule", record: row })}
              columns={[
                { header: "Rule", render: (row) => row.name },
                { header: "Change", align: "right", render: (row) => (toNumber(row.adjustment_percent) > 0 ? "+" : "") + toNumber(row.adjustment_percent) + "%" },
                { header: "Applies to", render: (row) => appliesTo(row) },
                { header: "Customer", render: (row) => (row.customer_id ? customerNames[row.customer_id] : "All") },
                { header: "Dates", render: (row) => dates(row) },
                { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
              ]}
            />
          </Card>
        </div>
      </div>
      <Modal title={editing?.kind === "category" ? "Category" : "Price rule"} open={editing !== null} onClose={() => setEditing(null)}>
        {editing && editing.kind === "category" && (
          <CategoryForm initial={editing.record} categories={categoryList} onSaved={afterSave} onCancel={() => setEditing(null)} />
        )}
        {editing && editing.kind === "rule" && (
          <RuleForm
            initial={editing.record}
            categories={categoryList}
            products={products.data || []}
            customers={customers.data || []}
            onSaved={afterSave}
            onCancel={() => setEditing(null)}
          />
        )}
      </Modal>
    </div>
  );
}
