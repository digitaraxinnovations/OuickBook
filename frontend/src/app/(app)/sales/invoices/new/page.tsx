"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, todayString, toNumber } from "@/lib/format";
import { customerService, invoiceService, productService } from "@/services";
import { InvoiceLineInput } from "@/types/inputs";

function emptyLine(): InvoiceLineInput {
  return { product_id: null, description: "", quantity: "1", rate: "" };
}

function lineAmount(line: InvoiceLineInput): number {
  return toNumber(line.quantity) * toNumber(line.rate);
}

export default function NewInvoicePage() {
  const { company } = useAuth();
  const router = useRouter();
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));

  const [customerId, setCustomerId] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(todayString());
  const [dueDate, setDueDate] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<InvoiceLineInput[]>([emptyLine()]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function updateLine(index: number, changes: Partial<InvoiceLineInput>) {
    const updated = lines.map((line, i) => (i === index ? { ...line, ...changes } : line));
    setLines(updated);
  }

  /** Picking a product fills in its description and price. */
  function chooseProduct(index: number, productId: string) {
    if (!productId) {
      updateLine(index, { product_id: null });
      return;
    }
    const product = (products.data || []).find((item) => item.id === Number(productId));
    if (product) {
      updateLine(index, {
        product_id: product.id,
        description: product.description || product.name,
        rate: product.sales_price,
      });
    }
  }

  function removeLine(index: number) {
    setLines(lines.filter((_, i) => i !== index));
  }

  let total = 0;
  for (const line of lines) {
    total += lineAmount(line);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const invoice = await invoiceService.create({
        customer_id: Number(customerId),
        invoice_date: invoiceDate,
        due_date: dueDate,
        memo: memo,
        lines: lines,
      });
      router.push("/sales/invoices/" + invoice.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the invoice.");
      setSaving(false);
    }
  }

  if (customers.loading || products.loading) {
    return <Loading />;
  }

  const customerOptions = (customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }));
  const productOptions = (products.data || []).map((product) => ({ value: product.id, label: product.name }));

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="New invoice" subtitle={"Invoice terms: " + company?.payment_terms_days + " days if no due date is set."} />
      <ErrorMessage message={error} />

      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <Field label="Customer" required>
              <Select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} placeholder="Choose a customer" options={customerOptions} />
            </Field>
            {customerOptions.length === 0 && <p className="mt-1 text-xs text-gray-500">Add a customer first under Sales → Customers.</p>}
          </div>
          <Field label="Invoice date" required>
            <TextInput type="date" required value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </Field>
          <Field label="Due date">
            <TextInput type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </Field>
        </div>

        <div className="mt-6 overflow-x-auto">
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
                <td className="py-2 pt-4 text-right font-medium">{formatMoney(lineAmount(line), company?.currency)}</td>
                <td className="py-2 pl-2">
                  {lines.length > 1 && (
                    <button type="button" onClick={() => removeLine(index)} className="mt-2 text-gray-400 hover:text-red-600" aria-label="Remove line">
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
          <Field label="Message on invoice">
            <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="flex items-start justify-end">
            <div className="text-right">
              <div className="text-sm text-gray-500">Total</div>
              <div className="text-3xl font-semibold">{formatMoney(total, company?.currency)}</div>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save invoice"}
        </Button>
      </div>
    </form>
  );
}
