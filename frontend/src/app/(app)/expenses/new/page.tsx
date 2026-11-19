"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { paymentMethodOptions } from "@/config/options";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, expenseService, vendorService } from "@/services";
import { PaymentMethod } from "@/types/models";

interface LineState {
  account_id: string;
  description: string;
  amount: string;
}

function emptyLine(): LineState {
  return { account_id: "", description: "", amount: "" };
}

export default function NewExpensePage() {
  const { company } = useAuth();
  const router = useRouter();
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const accounts = useLoad(() => accountService.list({ active_only: true }));

  const [vendorId, setVendorId] = useState("");
  const [paymentAccountId, setPaymentAccountId] = useState("");
  const [expenseDate, setExpenseDate] = useState(todayString());
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("CREDIT_CARD");
  const [referenceNo, setReferenceNo] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<LineState[]>([emptyLine()]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (vendors.loading || accounts.loading) {
    return <Loading />;
  }

  const allAccounts = accounts.data || [];
  // Pay from a bank account or a credit card.
  const paymentAccounts = allAccounts.filter(
    (account) => account.detail_type === "Bank" || account.detail_type === "Credit Card",
  );
  // Categories: expense accounts first, then everything else.
  const expenseAccounts = allAccounts.filter((account) => account.account_type === "EXPENSE");
  const otherAccounts = allAccounts.filter((account) => account.account_type !== "EXPENSE");
  const categoryOptions = [...expenseAccounts, ...otherAccounts].map((account) => ({ value: account.id, label: account.name }));

  function updateLine(index: number, changes: Partial<LineState>) {
    setLines(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  let total = 0;
  for (const line of lines) {
    total += toNumber(line.amount);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await expenseService.create({
        vendor_id: vendorId ? Number(vendorId) : null,
        payment_account_id: Number(paymentAccountId),
        expense_date: expenseDate,
        payment_method: paymentMethod,
        reference_no: referenceNo,
        memo: memo,
        lines: lines.map((line) => ({
          account_id: Number(line.account_id),
          description: line.description,
          amount: line.amount,
        })),
      });
      router.push("/expenses");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the expense.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="New expense" />
      <ErrorMessage message={error} />

      <Card>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Payee">
            <Select
              value={vendorId}
              onChange={(e) => setVendorId(e.target.value)}
              placeholder="(none)"
              options={(vendors.data || []).map((vendor) => ({ value: vendor.id, label: vendor.display_name }))}
            />
          </Field>
          <Field label="Payment account" required>
            <Select
              required
              value={paymentAccountId}
              onChange={(e) => setPaymentAccountId(e.target.value)}
              placeholder="Choose bank or card"
              options={paymentAccounts.map((account) => ({ value: account.id, label: account.name }))}
            />
          </Field>
          <Field label="Payment date" required>
            <TextInput type="date" required value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
          </Field>
          <Field label="Payment method">
            <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)} options={paymentMethodOptions} />
          </Field>
          <Field label="Ref no.">
            <TextInput value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
          </Field>
        </div>

        <h3 className="mt-6 mb-2 text-sm font-semibold uppercase text-gray-500">Category details</h3>
        <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="w-8 py-2">#</th>
              <th className="w-64 py-2">Category</th>
              <th className="py-2">Description</th>
              <th className="w-36 py-2">Amount</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="border-b border-gray-100">
                <td className="py-2 text-gray-500">{index + 1}</td>
                <td className="py-2 pr-2">
                  <Select required value={line.account_id} onChange={(e) => updateLine(index, { account_id: e.target.value })} placeholder="Choose a category" options={categoryOptions} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                </td>
                <td className="py-2 pr-2">
                  <TextInput type="number" step="0.01" min="0.01" required value={line.amount} onChange={(e) => updateLine(index, { amount: e.target.value })} />
                </td>
                <td className="py-2">
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
        </div>
        <Button type="button" variant="ghost" className="mt-3" onClick={() => setLines([...lines, emptyLine()])}>
          <Plus size={16} /> Add line
        </Button>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <Field label="Memo">
            <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="text-right">
            <div className="text-sm text-gray-500">Total</div>
            <div className="text-3xl font-semibold">{formatMoney(total, company?.currency)}</div>
          </div>
        </div>
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save expense"}
        </Button>
      </div>
    </form>
  );
}
