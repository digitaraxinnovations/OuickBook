"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, depositService } from "@/services";
import { UndepositedItem } from "@/types/models";

interface OtherLine {
  account_id: string;
  description: string;
  amount: string;
}

function itemKey(item: UndepositedItem): string {
  return item.source_type + "-" + item.source_id;
}

export default function NewDepositPage() {
  const { company } = useAuth();
  const router = useRouter();
  const currency = company?.currency;
  const waiting = useLoad(() => depositService.undeposited());
  const accounts = useLoad(() => accountService.list({ active_only: true }));

  const [bankAccountId, setBankAccountId] = useState("");
  const [depositDate, setDepositDate] = useState(todayString());
  const [memo, setMemo] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [otherLines, setOtherLines] = useState<OtherLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (waiting.loading || accounts.loading) {
    return <Loading />;
  }

  const items = waiting.data || [];
  const allAccounts = accounts.data || [];
  const bankAccounts = allAccounts.filter((account) => account.detail_type === "Bank");

  let total = 0;
  for (const item of items) {
    if (selected.includes(itemKey(item))) {
      total += toNumber(item.amount);
    }
  }
  for (const line of otherLines) {
    total += toNumber(line.amount);
  }

  function toggle(item: UndepositedItem) {
    const key = itemKey(item);
    setSelected(selected.includes(key) ? selected.filter((value) => value !== key) : [...selected, key]);
  }

  function updateOther(index: number, changes: Partial<OtherLine>) {
    setOtherLines(otherLines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await depositService.create({
        deposit_date: depositDate,
        bank_account_id: Number(bankAccountId),
        memo: memo,
        items: items
          .filter((item) => selected.includes(itemKey(item)))
          .map((item) => ({ source_type: item.source_type, source_id: item.source_id })),
        other_lines: otherLines.map((line) => ({ account_id: Number(line.account_id), description: line.description, amount: line.amount })),
      });
      router.push("/banking/deposits");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the deposit.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="Bank deposit" />
      <ErrorMessage message={error} />
      <Card>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Deposit to" required>
            <Select
              required
              value={bankAccountId}
              onChange={(e) => setBankAccountId(e.target.value)}
              placeholder="Choose a bank account"
              options={bankAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
            />
          </Field>
          <Field label="Date" required>
            <TextInput type="date" required value={depositDate} onChange={(e) => setDepositDate(e.target.value)} />
          </Field>
          <Field label="Memo">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
        </div>

        <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Select the payments included in this deposit</h3>
        {items.length === 0 ? (
          <p className="text-sm text-gray-500">Nothing is waiting in Undeposited Funds.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="w-8 py-2">
                  <input
                    type="checkbox"
                    checked={selected.length === items.length}
                    onChange={(e) => setSelected(e.target.checked ? items.map(itemKey) : [])}
                  />
                </th>
                <th className="py-2">Date</th>
                <th className="py-2">Received from</th>
                <th className="py-2">Reference</th>
                <th className="py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={itemKey(item)} className="border-b border-gray-100">
                  <td className="py-2">
                    <input type="checkbox" checked={selected.includes(itemKey(item))} onChange={() => toggle(item)} />
                  </td>
                  <td className="py-2">{formatDate(item.item_date)}</td>
                  <td className="py-2">{item.customer_name}</td>
                  <td className="py-2">{item.reference}</td>
                  <td className="py-2 text-right">{formatMoney(item.amount, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Add funds to this deposit</h3>
        {otherLines.map((line, index) => (
          <div key={index} className="mb-2 grid grid-cols-12 gap-2">
            <div className="col-span-4">
              <Select
                required
                value={line.account_id}
                onChange={(e) => updateOther(index, { account_id: e.target.value })}
                placeholder="Received from account"
                options={allAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
              />
            </div>
            <div className="col-span-5">
              <TextInput placeholder="Description" value={line.description} onChange={(e) => updateOther(index, { description: e.target.value })} />
            </div>
            <div className="col-span-2">
              <TextInput type="number" step="0.01" min="0.01" required value={line.amount} onChange={(e) => updateOther(index, { amount: e.target.value })} />
            </div>
            <button type="button" className="text-gray-400 hover:text-red-600" onClick={() => setOtherLines(otherLines.filter((_, i) => i !== index))} aria-label="Remove line">
              <Trash2 size={16} />
            </button>
          </div>
        ))}
        <Button type="button" variant="ghost" onClick={() => setOtherLines([...otherLines, { account_id: "", description: "", amount: "" }])}>
          <Plus size={16} /> Add line
        </Button>

        <div className="mt-6 text-right">
          <div className="text-sm text-gray-500">Deposit total</div>
          <div className="text-3xl font-semibold">{formatMoney(total, currency)}</div>
        </div>
      </Card>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || total <= 0}>
          {saving ? "Saving..." : "Save deposit"}
        </Button>
      </div>
    </form>
  );
}
