"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { emptySalesLine, SalesLinesEditor } from "@/components/sales/SalesLinesEditor";
import { computeSalesTotals, emptySalesAmounts, SalesTotals, taxRatesFor } from "@/components/sales/SalesTotals";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, customerService, invoiceService, productService, salesDocumentService, taxService, termsService } from "@/services";
import { SalesAmountsInput, SalesLineInput } from "@/types/inputs";
import { SalesDocumentSummary } from "@/types/models";

/** Open delayed charges (+) and delayed credits (-) for one customer. */
async function loadDelayedItems(customerId: string): Promise<SalesDocumentSummary[]> {
  if (!customerId) {
    return [];
  }
  const query = { customer_id: Number(customerId), status: "OPEN" };
  const charges = await salesDocumentService.listByType("DELAYED_CHARGE", query);
  const credits = await salesDocumentService.listByType("DELAYED_CREDIT", query);
  return [...charges, ...credits];
}

function signedTotal(item: SalesDocumentSummary): number {
  return item.doc_type === "DELAYED_CREDIT" ? -toNumber(item.total) : toNumber(item.total);
}

export default function NewInvoicePage() {
  const { company } = useAuth();
  const router = useRouter();
  const currency = company?.currency;
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));
  const terms = useLoad(() => termsService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const taxCodes = useLoad(() => taxService.codes(true));

  const [customerId, setCustomerId] = useState("");
  const [termsId, setTermsId] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(todayString());
  const [dueDate, setDueDate] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<SalesLineInput[]>([emptySalesLine()]);
  const [amounts, setAmounts] = useState<SalesAmountsInput>(emptySalesAmounts());
  const [selectedDelayed, setSelectedDelayed] = useState<number[]>([]);
  const [depositAmount, setDepositAmount] = useState("");
  const [depositAccountId, setDepositAccountId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const delayedItems = useLoad(() => loadDelayedItems(customerId), [customerId]);

  if (customers.loading || products.loading || terms.loading || accounts.loading || taxCodes.loading) {
    return <Loading />;
  }

  function chooseCustomer(value: string) {
    setCustomerId(value);
    setSelectedDelayed([]);
    // Use the customer's default terms, like the original product does.
    const customer = (customers.data || []).find((item) => item.id === Number(value));
    setTermsId(customer && customer.terms_id ? String(customer.terms_id) : "");
    setAmounts({ ...amounts, tax_code_id: customer ? customer.default_tax_code_id : null });
  }

  function toggleDelayed(id: number) {
    if (selectedDelayed.includes(id)) {
      setSelectedDelayed(selectedDelayed.filter((item) => item !== id));
    } else {
      setSelectedDelayed([...selectedDelayed, id]);
    }
  }

  // Lines typed by the user may be left empty when only delayed charges are added.
  const filledLines = lines.filter((line) => line.description || line.product_id || toNumber(line.rate) !== 0);
  let delayedTotal = 0;
  for (const item of delayedItems.data || []) {
    if (selectedDelayed.includes(item.id)) {
      delayedTotal += signedTotal(item);
    }
  }
  const chosenCustomer = (customers.data || []).find((item) => item.id === Number(customerId));
  const taxExempt = chosenCustomer ? chosenCustomer.tax_exempt : false;
  const totals = computeSalesTotals(filledLines, amounts, delayedTotal, taxRatesFor(taxCodes.data || [], amounts.tax_code_id, taxExempt));

  const depositAccounts = (accounts.data || []).filter(
    (account) => account.account_type === "ASSET" && account.system_key !== "accounts_receivable",
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const invoice = await invoiceService.create({
        customer_id: Number(customerId),
        invoice_date: invoiceDate,
        due_date: dueDate,
        terms_id: termsId ? Number(termsId) : null,
        memo: memo,
        lines: filledLines,
        tax_code_id: amounts.tax_code_id,
        discount_type: amounts.discount_type,
        discount_value: amounts.discount_value || "0",
        shipping_amount: amounts.shipping_amount || "0",
        delayed_document_ids: selectedDelayed,
        deposit_amount: depositAmount || "0",
        deposit_account_id: depositAccountId ? Number(depositAccountId) : null,
      });
      router.push("/sales/invoices/" + invoice.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the invoice.");
      setSaving(false);
    }
  }

  const customerOptions = (customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }));
  const termOptions = (terms.data || []).filter((term) => term.is_active).map((term) => ({ value: term.id, label: term.name }));

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="New invoice" />
      <ErrorMessage message={error} />

      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <Field label="Customer" required>
              <Select required value={customerId} onChange={(e) => chooseCustomer(e.target.value)} placeholder="Choose a customer" options={customerOptions} />
            </Field>
            {customerOptions.length === 0 && <p className="mt-1 text-xs text-gray-500">Add a customer first under Sales → Customers.</p>}
          </div>
          <Field label="Terms">
            <Select value={termsId} onChange={(e) => setTermsId(e.target.value)} placeholder={"Company default (" + company?.payment_terms_days + " days)"} options={termOptions} />
          </Field>
          <div />
          <Field label="Invoice date" required>
            <TextInput type="date" required value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
          </Field>
          <Field label="Due date (empty = from terms)">
            <TextInput type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </Field>
        </div>

        {(delayedItems.data || []).length > 0 && (
          <div className="mt-6 rounded-md border border-amber-200 bg-amber-50 p-4">
            <div className="mb-2 text-sm font-semibold text-amber-900">Add to this invoice</div>
            {(delayedItems.data || []).map((item) => (
              <label key={item.id} className="flex items-center gap-2 py-1 text-sm">
                <input type="checkbox" checked={selectedDelayed.includes(item.id)} onChange={() => toggleDelayed(item.id)} />
                {item.doc_type === "DELAYED_CREDIT" ? "Delayed credit" : "Delayed charge"} {item.doc_number}
                <span className="ml-auto font-medium">{formatMoney(signedTotal(item), currency)}</span>
              </label>
            ))}
          </div>
        )}

        <div className="mt-6">
          <SalesLinesEditor lines={lines} onChange={setLines} products={products.data || []} currency={currency} />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <Field label="Message on invoice">
              <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Deposit received now">
                <TextInput type="number" step="0.01" min="0" value={depositAmount} onChange={(e) => setDepositAmount(e.target.value)} placeholder="0.00" />
              </Field>
              <Field label="Deposit to">
                <Select
                  value={depositAccountId}
                  onChange={(e) => setDepositAccountId(e.target.value)}
                  placeholder="Undeposited Funds"
                  options={depositAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
                />
              </Field>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <SalesTotals
              lines={filledLines}
              amounts={amounts}
              onChange={setAmounts}
              taxCodes={taxCodes.data || []}
              taxExempt={taxExempt}
              currency={currency}
              extraLinesTotal={delayedTotal}
            />
            {toNumber(depositAmount) > 0 && (
              <div className="w-full max-w-sm text-right text-sm">
                Balance due after deposit: <strong>{formatMoney(totals.total - toNumber(depositAmount), currency)}</strong>
              </div>
            )}
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
