"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { paymentMethodOptions } from "@/config/options";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, customerService, invoiceService, paymentService } from "@/services";
import { CustomerCredit, InvoiceSummary, PaymentMethod } from "@/types/models";

interface CustomerOpenItems {
  invoices: InvoiceSummary[];
  credits: CustomerCredit[];
}

async function loadOpenItems(customerId: string): Promise<CustomerOpenItems> {
  if (!customerId) {
    return { invoices: [], credits: [] };
  }
  const id = Number(customerId);
  const all = await invoiceService.listSummaries({ customer_id: id });
  const open = all.filter((invoice) => toNumber(invoice.balance_due) > 0).reverse(); // oldest first
  const credits = await customerService.credits(id);
  return { invoices: open, credits: credits };
}

function creditKey(credit: CustomerCredit): string {
  return credit.source_type + "-" + credit.source_id;
}

/** Fill amounts from the oldest invoice to the newest, like the original product. */
function autoApply(invoices: InvoiceSummary[], available: number): Record<number, string> {
  const result: Record<number, string> = {};
  let left = available;
  for (const invoice of invoices) {
    if (left <= 0) {
      break;
    }
    const amount = Math.min(left, toNumber(invoice.balance_due));
    result[invoice.id] = amount.toFixed(2);
    left = Math.round((left - amount) * 100) / 100;
  }
  return result;
}

export default function ReceivePaymentPage() {
  const { company } = useAuth();
  const router = useRouter();
  const currency = company?.currency;
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const accounts = useLoad(() => accountService.list({ active_only: true }));

  const [customerId, setCustomerId] = useState("");
  const [paymentDate, setPaymentDate] = useState(todayString());
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("BANK_TRANSFER");
  const [referenceNo, setReferenceNo] = useState("");
  const [depositAccountId, setDepositAccountId] = useState("");
  const [memo, setMemo] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [applied, setApplied] = useState<Record<number, string>>({});
  const [creditsUsed, setCreditsUsed] = useState<Record<string, string>>({});
  const [preselectInvoice, setPreselectInvoice] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const openItems = useLoad(() => loadOpenItems(customerId), [customerId]);

  // Coming from an invoice: /sales/payments/new?customer=1&invoice=5
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("customer")) {
      setCustomerId(params.get("customer") || "");
      setPreselectInvoice(params.get("invoice") ? Number(params.get("invoice")) : null);
    }
  }, []);

  // When the invoice list arrives, fill in the invoice we came from.
  useEffect(() => {
    if (preselectInvoice === null || !openItems.data) {
      return;
    }
    const invoice = openItems.data.invoices.find((item) => item.id === preselectInvoice);
    if (invoice) {
      setApplied({ [invoice.id]: invoice.balance_due });
      setAmount(invoice.balance_due);
    }
    setPreselectInvoice(null);
  }, [preselectInvoice, openItems.data]);

  if (customers.loading || accounts.loading) {
    return <Loading />;
  }

  const invoices = openItems.data?.invoices || [];
  const credits = openItems.data?.credits || [];

  let appliedTotal = 0;
  for (const invoice of invoices) {
    appliedTotal += toNumber(applied[invoice.id]);
  }
  let creditsTotal = 0;
  for (const credit of credits) {
    creditsTotal += toNumber(creditsUsed[creditKey(credit)]);
  }
  const amountReceived = toNumber(amount);
  const leftOver = Math.round((amountReceived + creditsTotal - appliedTotal) * 100) / 100;

  function chooseCustomer(value: string) {
    setCustomerId(value);
    setApplied({});
    setCreditsUsed({});
  }

  function changeAmount(value: string) {
    setAmount(value);
    setApplied(autoApply(invoices, toNumber(value) + creditsTotal));
  }

  function toggleInvoice(invoice: InvoiceSummary, checked: boolean) {
    const copy = { ...applied };
    if (checked) {
      copy[invoice.id] = invoice.balance_due;
    } else {
      delete copy[invoice.id];
    }
    setApplied(copy);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const applications = invoices
      .filter((invoice) => toNumber(applied[invoice.id]) > 0)
      .map((invoice) => ({ invoice_id: invoice.id, amount: applied[invoice.id] }));
    const creditList = credits
      .filter((credit) => toNumber(creditsUsed[creditKey(credit)]) > 0)
      .map((credit) => ({ source_type: credit.source_type, source_id: credit.source_id, amount: creditsUsed[creditKey(credit)] }));
    try {
      await paymentService.create({
        customer_id: Number(customerId),
        payment_date: paymentDate,
        amount: amount || "0",
        payment_method: method,
        reference_no: referenceNo,
        deposit_account_id: depositAccountId ? Number(depositAccountId) : null,
        memo: memo,
        exchange_rate: foreignCurrency && exchangeRate ? exchangeRate : null,
        applications: applications,
        credits: creditList,
      });
      router.push("/sales/payments");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the payment.");
      setSaving(false);
    }
  }

  const chosen = (customers.data || []).find((customer) => customer.id === Number(customerId));
  const foreignCurrency = chosen ? chosen.currency_code : null;

  const depositAccounts = (accounts.data || []).filter(
    (account) => account.account_type === "ASSET" && account.system_key !== "accounts_receivable",
  );

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="Receive payment" subtitle="Pay one or more invoices. Extra money stays with the customer as a credit." />
      <ErrorMessage message={error} />

      <Card>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Customer" required>
            <Select
              required
              value={customerId}
              onChange={(e) => chooseCustomer(e.target.value)}
              placeholder="Choose a customer"
              options={(customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }))}
            />
          </Field>
          <Field label="Payment date" required>
            <TextInput type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
          </Field>
          <Field label="Amount received">
            <TextInput type="number" step="0.01" min="0" value={amount} onChange={(e) => changeAmount(e.target.value)} placeholder="0.00" />
          </Field>
          {foreignCurrency && (
            <Field label={"Exchange rate (1 " + foreignCurrency + " = ? " + company?.currency + ")"}>
              <TextInput type="number" step="0.00000001" min="0" value={exchangeRate} onChange={(e) => setExchangeRate(e.target.value)} placeholder="Latest saved rate" />
            </Field>
          )}
          <Field label="Payment method">
            <Select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} options={paymentMethodOptions} />
          </Field>
          <Field label="Reference no.">
            <TextInput value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
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

        {customerId && (
          <>
            <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Outstanding invoices</h3>
            {openItems.loading && <Loading />}
            {!openItems.loading && invoices.length === 0 && <p className="text-sm text-gray-500">This customer has no unpaid invoices.</p>}
            {invoices.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                    <tr>
                      <th className="w-8 py-2"></th>
                      <th className="py-2">Invoice</th>
                      <th className="py-2">Due date</th>
                      <th className="py-2 text-right">Open balance</th>
                      <th className="w-40 py-2 text-right">Payment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((invoice) => (
                      <tr key={invoice.id} className="border-b border-gray-100">
                        <td className="py-2">
                          <input type="checkbox" checked={toNumber(applied[invoice.id]) > 0} onChange={(e) => toggleInvoice(invoice, e.target.checked)} />
                        </td>
                        <td className="py-2">
                          Invoice {invoice.invoice_number} <span className="text-gray-500">({formatDate(invoice.invoice_date)})</span>
                        </td>
                        <td className={"py-2 " + (invoice.is_overdue ? "text-red-600" : "")}>{formatDate(invoice.due_date)}</td>
                        <td className="py-2 text-right">{formatMoney(invoice.balance_due, currency)}</td>
                        <td className="py-2 pl-4">
                          <TextInput
                            type="number"
                            step="0.01"
                            min="0"
                            max={invoice.balance_due}
                            className="text-right"
                            value={applied[invoice.id] || ""}
                            onChange={(e) => setApplied({ ...applied, [invoice.id]: e.target.value })}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {credits.length > 0 && (
              <>
                <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Credits you can use</h3>
                <table className="w-full text-sm">
                  <tbody>
                    {credits.map((credit) => (
                      <tr key={creditKey(credit)} className="border-b border-gray-100">
                        <td className="py-2">{credit.reference}</td>
                        <td className="py-2 text-gray-500">{formatDate(credit.credit_date)}</td>
                        <td className="py-2 text-right">Available {formatMoney(credit.remaining, currency)}</td>
                        <td className="w-40 py-2 pl-4">
                          <TextInput
                            type="number"
                            step="0.01"
                            min="0"
                            max={credit.remaining}
                            className="text-right"
                            value={creditsUsed[creditKey(credit)] || ""}
                            onChange={(e) => setCreditsUsed({ ...creditsUsed, [creditKey(credit)]: e.target.value })}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </>
        )}

        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <Field label="Memo">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="ml-auto w-full max-w-xs space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Amount received</span>
              <span>{formatMoney(amountReceived, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span>Credits used</span>
              <span>{formatMoney(creditsTotal, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span>Applied to invoices</span>
              <span>{formatMoney(appliedTotal, currency)}</span>
            </div>
            <div className={"flex justify-between border-t border-gray-200 pt-2 font-semibold " + (leftOver < 0 ? "text-red-600" : "")}>
              <span>{leftOver < 0 ? "Short by" : "Amount to credit"}</span>
              <span>{formatMoney(Math.abs(leftOver), currency)}</span>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || leftOver < 0 || !customerId}>
          {saving ? "Saving..." : "Save payment"}
        </Button>
      </div>
    </form>
  );
}
