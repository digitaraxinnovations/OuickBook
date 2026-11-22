"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { paymentMethodOptions } from "@/config/options";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, todayString, toNumber } from "@/lib/format";
import { purchasableProducts } from "@/components/purchases/PurchaseLinesEditor";
import { accountService, attachmentService, checkService, customerService, expenseService, productService, vendorService } from "@/services";
import { ExpenseKind, PaymentMethod } from "@/types/models";
import { emptyTracking, TrackingFields } from "@/components/forms/TrackingFields";
import { TrackingInput } from "@/types/inputs";

interface LineState {
  account_id: string;
  product_id: string;
  quantity: string;
  description: string;
  amount: string;
  customer_id: string;
}

function emptyLine(): LineState {
  return { account_id: "", product_id: "", quantity: "1", description: "", amount: "", customer_id: "" };
}

/** New expense, or new check when the URL has ?kind=CHECK. ?receipt=ID attaches an uploaded receipt. */
export default function NewExpensePage() {
  const { company } = useAuth();
  const router = useRouter();
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));

  const [kind, setKind] = useState<ExpenseKind>("EXPENSE");
  const [receiptId, setReceiptId] = useState<number | null>(null);
  const [vendorId, setVendorId] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [paymentAccountId, setPaymentAccountId] = useState("");
  const [expenseDate, setExpenseDate] = useState(todayString());
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("CREDIT_CARD");
  const [referenceNo, setReferenceNo] = useState("");
  const [checkNumber, setCheckNumber] = useState("");
  const [printLater, setPrintLater] = useState(false);
  const [memo, setMemo] = useState("");
  const [tracking, setTracking] = useState<TrackingInput>(emptyTracking());
  const [lines, setLines] = useState<LineState[]>([emptyLine()]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("kind") === "CHECK" || params.get("kind") === "CARD_CREDIT") {
      setKind(params.get("kind") as ExpenseKind);
    }
    if (params.get("receipt")) {
      setReceiptId(Number(params.get("receipt")));
    }
  }, []);

  // Checks: suggest the next check number for the chosen bank account.
  useEffect(() => {
    if (kind !== "CHECK" || !paymentAccountId) {
      return;
    }
    checkService
      .nextNumber(Number(paymentAccountId))
      .then((result) => setCheckNumber(String(result.next_check_number)))
      .catch(() => setCheckNumber(""));
  }, [kind, paymentAccountId]);

  if (vendors.loading || accounts.loading || customers.loading || products.loading) {
    return <Loading />;
  }

  const isCheck = kind === "CHECK";
  const isCardCredit = kind === "CARD_CREDIT";
  const allAccounts = accounts.data || [];
  const paymentAccounts = allAccounts.filter((account) => {
    if (isCardCredit) {
      return account.detail_type === "Credit Card";
    }
    return account.detail_type === "Bank" || (!isCheck && account.detail_type === "Credit Card");
  });
  const expenseAccounts = allAccounts.filter((account) => account.account_type === "EXPENSE");
  const otherAccounts = allAccounts.filter((account) => account.account_type !== "EXPENSE");
  const categoryOptions = [...expenseAccounts, ...otherAccounts].map((account) => ({ value: account.id, label: account.full_name }));
  const customerOptions = (customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }));

  function updateLine(index: number, changes: Partial<LineState>) {
    setLines(lines.map((line, i) => (i === index ? { ...line, ...changes } : line)));
  }

  const items = purchasableProducts(products.data || []);
  const productOptions = items.map((product) => ({ value: product.id, label: product.name }));

  function findItem(productId: string) {
    return items.find((item) => item.id === Number(productId));
  }

  /** Picking an item fills in its description, cost and expense account. */
  function chooseProduct(index: number, productId: string) {
    const product = findItem(productId);
    if (!product) {
      updateLine(index, { product_id: "" });
      return;
    }
    const quantity = toNumber(lines[index].quantity) || 1;
    updateLine(index, {
      product_id: String(product.id),
      description: product.purchase_description || product.name,
      amount: (toNumber(product.purchase_cost) * quantity).toFixed(2),
      account_id: product.expense_account_id ? String(product.expense_account_id) : "",
    });
  }

  function isInventoryLine(line: LineState): boolean {
    const product = findItem(line.product_id);
    return product !== undefined && product.product_type === "INVENTORY";
  }

  let total = 0;
  for (const line of lines) {
    total += toNumber(line.amount);
  }

  // A foreign currency vendor's expense is entered in their currency.
  const chosenVendor = (vendors.data || []).find((item) => item.id === Number(vendorId));
  const foreignCode = chosenVendor && chosenVendor.currency_code ? chosenVendor.currency_code : null;
  const formCurrency = foreignCode || company?.currency;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const expense = await expenseService.create({
        kind: kind,
        vendor_id: vendorId ? Number(vendorId) : null,
        payment_account_id: Number(paymentAccountId),
        expense_date: expenseDate,
        payment_method: isCheck ? "CHECK" : isCardCredit ? "CREDIT_CARD" : paymentMethod,
        reference_no: referenceNo,
        check_number: isCheck && !printLater ? checkNumber : "",
        print_later: isCheck && printLater,
        memo: memo,
        exchange_rate: foreignCode && exchangeRate ? exchangeRate : null,
        ...tracking,
        lines: lines.map((line) => ({
          account_id: line.account_id && !isInventoryLine(line) ? Number(line.account_id) : null,
          product_id: line.product_id ? Number(line.product_id) : null,
          quantity: line.quantity || "1",
          description: line.description,
          amount: line.amount,
          customer_id: line.customer_id ? Number(line.customer_id) : null,
        })),
      });
      if (receiptId !== null) {
        await attachmentService.link(receiptId, "EXPENSE", expense.id);
      }
      router.push("/expenses/" + expense.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader
        title={isCheck ? "Write check" : isCardCredit ? "Credit card credit" : "New expense"}
        subtitle={receiptId !== null ? "The receipt you chose will be attached when you save." : undefined}
      />
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
          <Field label={isCheck ? "Bank account" : isCardCredit ? "Credit card" : "Payment account"} required>
            <Select
              required
              value={paymentAccountId}
              onChange={(e) => setPaymentAccountId(e.target.value)}
              placeholder={isCheck ? "Choose a bank account" : "Choose bank or card"}
              options={paymentAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
            />
          </Field>
          <Field label="Payment date" required>
            <TextInput type="date" required value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
          </Field>
          {foreignCode && (
            <Field label={"Exchange rate (1 " + foreignCode + " = ? " + company?.currency + ")"}>
              <TextInput type="number" step="0.00000001" min="0" value={exchangeRate} onChange={(e) => setExchangeRate(e.target.value)} placeholder="Latest saved rate" />
            </Field>
          )}
          {isCardCredit ? (
            <Field label="Ref no.">
              <TextInput value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
            </Field>
          ) : isCheck ? (
            <>
              <Field label="Check no.">
                <TextInput value={checkNumber} disabled={printLater} onChange={(e) => setCheckNumber(e.target.value)} />
              </Field>
              <label className="flex items-center gap-2 pt-6 text-sm">
                <input type="checkbox" checked={printLater} onChange={(e) => setPrintLater(e.target.checked)} />
                Print later (number it when printing)
              </label>
            </>
          ) : (
            <>
              <Field label="Payment method">
                <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)} options={paymentMethodOptions} />
              </Field>
              <Field label="Ref no.">
                <TextInput value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
              </Field>
            </>
          )}
        </div>
        <div className="mt-4">
          <TrackingFields value={tracking} onChange={setTracking} />
        </div>

        <h3 className="mt-6 mb-2 text-sm font-semibold uppercase text-gray-500">Category and item details</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] text-sm">
            <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="w-8 py-2">#</th>
                <th className="w-44 py-2">Product / service</th>
                <th className="w-52 py-2">Category</th>
                <th className="py-2">Description</th>
                <th className="w-20 py-2">Qty</th>
                <th className="w-32 py-2">Amount</th>
                <th className="w-44 py-2 pl-2">Billable to</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="py-2 text-gray-500">{index + 1}</td>
                  <td className="py-2 pr-2">
                    <Select value={line.product_id} onChange={(e) => chooseProduct(index, e.target.value)} placeholder="-" options={productOptions} />
                  </td>
                  <td className="py-2 pr-2">
                    {isInventoryLine(line) ? (
                      <span className="text-gray-500">Inventory Asset</span>
                    ) : (
                      <Select
                        required={!line.product_id}
                        value={line.account_id}
                        onChange={(e) => updateLine(index, { account_id: e.target.value })}
                        placeholder={line.product_id ? "Item's account" : "Choose a category"}
                        options={categoryOptions}
                      />
                    )}
                  </td>
                  <td className="py-2 pr-2">
                    <TextInput value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} />
                  </td>
                  <td className="py-2 pr-2">
                    <TextInput type="number" step="0.01" min="0.01" value={line.quantity} onChange={(e) => updateLine(index, { quantity: e.target.value })} />
                  </td>
                  <td className="py-2 pr-2">
                    <TextInput type="number" step="0.01" min="0.01" required value={line.amount} onChange={(e) => updateLine(index, { amount: e.target.value })} />
                  </td>
                  <td className="py-2 pl-2">
                    <Select value={line.customer_id} onChange={(e) => updateLine(index, { customer_id: e.target.value })} placeholder="-" options={customerOptions} />
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
        </div>
        <Button type="button" variant="ghost" className="mt-3" onClick={() => setLines([...lines, emptyLine()])}>
          <Plus size={16} /> Add line
        </Button>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Field label="Memo">
            <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="text-right">
            <div className="text-sm text-gray-500">Total</div>
            <div className="text-3xl font-semibold">{formatMoney(total, formCurrency)}</div>
          </div>
        </div>
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : isCheck ? "Save check" : isCardCredit ? "Save credit" : "Save expense"}
        </Button>
      </div>
    </form>
  );
}
