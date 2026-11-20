"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { accountService, bankingService, vendorService } from "@/services";
import { BankRuleInput } from "@/types/inputs";
import { Account, BankRule, BankRuleDirection, RuleCondition, Vendor } from "@/types/models";

const operatorOptions = [
  { value: "contains", label: "contains" },
  { value: "not_contains", label: "does not contain" },
  { value: "equals", label: "is exactly" },
  { value: "starts_with", label: "starts with" },
  { value: "ends_with", label: "ends with" },
  { value: "greater_than", label: "is more than" },
  { value: "less_than", label: "is less than" },
];

const directionLabels: Record<string, string> = { MONEY_OUT: "Money out", MONEY_IN: "Money in", ANY: "Money in or out" };

function emptyRule(): BankRuleInput {
  return {
    name: "",
    priority: 100,
    account_id: null,
    direction: "MONEY_OUT",
    match_type: "ALL",
    conditions: [{ field: "description", operator: "contains", value: "" }],
    category_account_id: 0,
    vendor_id: null,
    auto_add: false,
    is_active: true,
  };
}

function ruleToInput(rule: BankRule): BankRuleInput {
  return {
    name: rule.name,
    priority: rule.priority,
    account_id: rule.account_id,
    direction: rule.direction,
    match_type: rule.match_type,
    conditions: rule.conditions,
    category_account_id: rule.category_account.id,
    vendor_id: rule.vendor_id,
    auto_add: rule.auto_add,
    is_active: rule.is_active,
  };
}

interface RuleFormProps {
  initial: BankRuleInput;
  accounts: Account[];
  vendors: Vendor[];
  onSave: (input: BankRuleInput) => Promise<void>;
  onCancel: () => void;
}

function RuleForm({ initial, accounts, vendors, onSave, onCancel }: RuleFormProps) {
  const [rule, setRule] = useState<BankRuleInput>(initial);
  const [error, setError] = useState<string | null>(null);

  function update(changes: Partial<BankRuleInput>) {
    setRule({ ...rule, ...changes });
  }

  function updateCondition(index: number, changes: Partial<RuleCondition>) {
    update({ conditions: rule.conditions.map((condition, i) => (i === index ? { ...condition, ...changes } : condition)) });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await onSave(rule);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  const bankAccounts = accounts.filter((account) => account.detail_type === "Bank" || account.detail_type === "Credit Card");

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <Field label="Rule name" required>
            <TextInput required value={rule.name} onChange={(e) => update({ name: e.target.value })} />
          </Field>
        </div>
        <Field label="Priority (1 = first)">
          <TextInput type="number" min="1" value={rule.priority} onChange={(e) => update({ priority: Number(e.target.value) })} />
        </Field>
        <Field label="Apply to">
          <Select
            value={rule.direction}
            onChange={(e) => update({ direction: e.target.value as BankRuleDirection })}
            options={[
              { value: "MONEY_OUT", label: "Money out" },
              { value: "MONEY_IN", label: "Money in" },
              { value: "ANY", label: "Both" },
            ]}
          />
        </Field>
        <Field label="In account">
          <Select
            value={rule.account_id ?? ""}
            onChange={(e) => update({ account_id: e.target.value ? Number(e.target.value) : null })}
            placeholder="All bank and card accounts"
            options={bankAccounts.map((account) => ({ value: account.id, label: account.name }))}
          />
        </Field>
        <Field label="When">
          <Select
            value={rule.match_type}
            onChange={(e) => update({ match_type: e.target.value as "ALL" | "ANY" })}
            options={[
              { value: "ALL", label: "All conditions match" },
              { value: "ANY", label: "Any condition matches" },
            ]}
          />
        </Field>
      </div>

      <div className="space-y-2 rounded-md bg-gray-50 p-3">
        {rule.conditions.map((condition, index) => (
          <div key={index} className="flex items-center gap-2">
            <Select
              className="w-36!"
              value={condition.field}
              onChange={(e) => updateCondition(index, { field: e.target.value as "description" | "amount" })}
              options={[
                { value: "description", label: "Description" },
                { value: "amount", label: "Amount" },
              ]}
            />
            <Select className="w-44!" value={condition.operator} onChange={(e) => updateCondition(index, { operator: e.target.value })} options={operatorOptions} />
            <TextInput required value={condition.value} onChange={(e) => updateCondition(index, { value: e.target.value })} />
            {rule.conditions.length > 1 && (
              <button type="button" onClick={() => update({ conditions: rule.conditions.filter((_, i) => i !== index) })} className="text-gray-400 hover:text-red-600" aria-label="Remove condition">
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        <Button
          type="button"
          variant="ghost"
          onClick={() => update({ conditions: [...rule.conditions, { field: "description", operator: "contains", value: "" }] })}
        >
          <Plus size={16} /> Add condition
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Then categorize as" required>
          <Select
            required
            value={rule.category_account_id || ""}
            onChange={(e) => update({ category_account_id: Number(e.target.value) })}
            placeholder="Choose a category"
            options={accounts.map((account) => ({ value: account.id, label: account.full_name }))}
          />
        </Field>
        <Field label="Payee">
          <Select
            value={rule.vendor_id ?? ""}
            onChange={(e) => update({ vendor_id: e.target.value ? Number(e.target.value) : null })}
            placeholder="(none)"
            options={vendors.map((vendor) => ({ value: vendor.id, label: vendor.display_name }))}
          />
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={rule.auto_add} onChange={(e) => update({ auto_add: e.target.checked })} />
        Automatically add matching lines (no review needed)
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={rule.is_active} onChange={(e) => update({ is_active: e.target.checked })} />
        Active
      </label>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save rule</Button>
      </div>
    </form>
  );
}

function describeConditions(rule: BankRule): string {
  const parts = rule.conditions.map((condition) => condition.field + " " + condition.operator.replace("_", " ") + ' "' + condition.value + '"');
  return parts.join(rule.match_type === "ALL" ? " and " : " or ");
}

export default function BankRulesPage() {
  const rules = useLoad(() => bankingService.rules());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const [editing, setEditing] = useState<BankRule | null>(null);
  const [open, setOpen] = useState(false);

  async function save(input: BankRuleInput) {
    if (editing) {
      await bankingService.updateRule(editing.id, input);
    } else {
      await bankingService.createRule(input);
    }
    setOpen(false);
    rules.reload();
  }

  async function remove(rule: BankRule) {
    if (window.confirm('Delete the rule "' + rule.name + '"?')) {
      await bankingService.deleteRule(rule.id);
      rules.reload();
    }
  }

  return (
    <div>
      <PageHeader
        title="Bank rules"
        subtitle="Categorize bank lines automatically. Rules run when you upload a statement, in priority order."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus size={16} /> New rule
          </Button>
        }
      />
      <ErrorMessage message={rules.error} />
      {rules.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={rules.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => {
            setEditing(row);
            setOpen(true);
          }}
          emptyText="No rules yet."
          columns={[
            { header: "Priority", render: (row) => row.priority },
            { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "Applies to", render: (row) => directionLabels[row.direction] },
            { header: "Conditions", render: (row) => describeConditions(row) },
            { header: "Category", render: (row) => row.category_account.name },
            { header: "Auto-add", render: (row) => (row.auto_add ? "Yes" : "") },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Off") },
            {
              header: "",
              align: "right",
              render: (row) => (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    remove(row);
                  }}
                  className="text-gray-400 hover:text-red-600"
                  aria-label="Delete rule"
                >
                  <Trash2 size={16} />
                </button>
              ),
            },
          ]}
        />
      )}
      <Modal title={editing ? "Edit rule" : "New rule"} open={open} onClose={() => setOpen(false)} wide>
        <RuleForm
          key={editing ? editing.id : "new"}
          initial={editing ? ruleToInput(editing) : emptyRule()}
          accounts={accounts.data || []}
          vendors={vendors.data || []}
          onSave={save}
          onCancel={() => setOpen(false)}
        />
      </Modal>
    </div>
  );
}
