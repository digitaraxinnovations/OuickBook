"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, billPaymentService, purchaseService, vendorService } from "@/services";
import { PaymentMethod, PurchaseDocumentSummary } from "@/types/models";

const methodOptions = [
  { value: "CHECK", label: "Check" },
  { value: "BANK_TRANSFER", label: "Bank transfer" },
  { value: "CREDIT_CARD", label: "Credit card" },
  { value: "CASH", label: "Cash" },
];

/** Unpaid bills (and, for one vendor, their unused credits). */
async function loadOpenItems(vendorId: string) {
  const query = vendorId ? { vendor_id: Number(vendorId) } : {};
  const open = await purchaseService.listByType("BILL", { ...query, status: "OPEN" });
  const partly = await purchaseService.listByType("BILL", { ...query, status: "PARTIALLY_PAID" });
  const bills = [...open, ...partly].sort((a, b) => ((a.due_date || "") < (b.due_date || "") ? -1 : 1));
  let credits: PurchaseDocumentSummary[] = [];
  if (vendorId) {
    credits = await purchaseService.listByType("VENDOR_CREDIT", { vendor_id: Number(vendorId), status: "OPEN" });
  }
  return { bills: bills, credits: credits };
}

/**
 * The "Pay bills" screen. Choose bills from any vendors and pay them in one go -
 * one payment (and one check) is made per vendor. Choose a single vendor to also
 * use their vendor credits.
 */
export default function PayBillsPage() {
  const { company } = useAuth();
  const router = useRouter();
  const currency = company?.currency;
  const vendors = useLoad(() => vendorService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));

  const [vendorId, setVendorId] = useState("");
  const [paymentDate, setPaymentDate] = useState(todayString());
  const [paymentAccountId, setPaymentAccountId] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("CHECK");
  const [printLater, setPrintLater] = useState(true);
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [creditAmounts, setCreditAmounts] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const items = useLoad(() => loadOpenItems(vendorId), [vendorId]);

  useEffect(() => {
    const vendor = new URLSearchParams(window.location.search).get("vendor");
    if (vendor) {
      setVendorId(vendor);
    }
  }, []);

  if (vendors.loading || accounts.loading) {
    return <Loading />;
  }

  const bills = items.data?.bills || [];
  const credits = items.data?.credits || [];
  const allAccounts = accounts.data || [];
  const payFromAccounts = allAccounts.filter(
    (account) => account.detail_type === "Bank" || (method === "CREDIT_CARD" && account.detail_type === "Credit Card"),
  );

  let billsTotal = 0;
  for (const bill of bills) {
    billsTotal += toNumber(amounts[bill.id]);
  }
  let creditsTotal = 0;
  for (const credit of credits) {
    creditsTotal += toNumber(creditAmounts[credit.id]);
  }

  function toggle(bill: PurchaseDocumentSummary, checked: boolean) {
    const copy = { ...amounts };
    if (checked) {
      copy[bill.id] = bill.balance;
    } else {
      delete copy[bill.id];
    }
    setAmounts(copy);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const chosen = bills
      .filter((bill) => toNumber(amounts[bill.id]) > 0)
      .map((bill) => ({ bill_id: bill.id, amount: amounts[bill.id] }));
    try {
      if (vendorId) {
        await billPaymentService.create({
          vendor_id: Number(vendorId),
          payment_date: paymentDate,
          payment_account_id: Number(paymentAccountId),
          payment_method: method,
          check_number: "",
          print_later: method === "CHECK" && printLater,
          memo: "",
          applications: chosen,
          credits: credits
            .filter((credit) => toNumber(creditAmounts[credit.id]) > 0)
            .map((credit) => ({ vendor_credit_id: credit.id, amount: creditAmounts[credit.id] })),
        });
      } else {
        await billPaymentService.payBatch({
          payment_date: paymentDate,
          payment_account_id: Number(paymentAccountId),
          payment_method: method,
          print_later: method === "CHECK" && printLater,
          bills: chosen,
        });
      }
      router.push(method === "CHECK" && printLater ? "/expenses/print-checks" : "/expenses/bill-payments");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not pay the bills.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="Pay bills" subtitle="Tick the bills to pay. One payment is made for each vendor." />
      <ErrorMessage message={error} />
      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <Field label="Vendor">
            <Select
              value={vendorId}
              onChange={(e) => {
                setVendorId(e.target.value);
                setAmounts({});
                setCreditAmounts({});
              }}
              placeholder="All vendors"
              options={(vendors.data || []).map((vendor) => ({ value: vendor.id, label: vendor.display_name }))}
            />
          </Field>
          <Field label="Payment method">
            <Select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} options={methodOptions} />
          </Field>
          <Field label="Pay from" required>
            <Select
              required
              value={paymentAccountId}
              onChange={(e) => setPaymentAccountId(e.target.value)}
              placeholder="Choose an account"
              options={payFromAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
            />
          </Field>
          <Field label="Payment date" required>
            <TextInput type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
          </Field>
        </div>
        {method === "CHECK" && (
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={printLater} onChange={(e) => setPrintLater(e.target.checked)} />
            Print checks later (otherwise the next check numbers are used now)
          </label>
        )}

        <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Unpaid bills</h3>
        {items.loading && <Loading />}
        {!items.loading && bills.length === 0 && <p className="text-sm text-gray-500">No unpaid bills.</p>}
        {bills.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="w-8 py-2"></th>
                  <th className="py-2">Vendor</th>
                  <th className="py-2">Bill no.</th>
                  <th className="py-2">Due date</th>
                  <th className="py-2 text-right">Open balance</th>
                  <th className="w-40 py-2 text-right">Payment</th>
                </tr>
              </thead>
              <tbody>
                {bills.map((bill) => (
                  <tr key={bill.id} className="border-b border-gray-100">
                    <td className="py-2">
                      <input type="checkbox" checked={toNumber(amounts[bill.id]) > 0} onChange={(e) => toggle(bill, e.target.checked)} />
                    </td>
                    <td className="py-2">{bill.vendor.display_name}</td>
                    <td className="py-2">{bill.doc_number || "-"}</td>
                    <td className={"py-2 " + (bill.is_overdue ? "text-red-600" : "")}>{formatDate(bill.due_date)}</td>
                    <td className="py-2 text-right">{formatMoney(bill.balance, currency)}</td>
                    <td className="py-2 pl-4">
                      <TextInput
                        type="number"
                        step="0.01"
                        min="0"
                        max={bill.balance}
                        className="text-right"
                        value={amounts[bill.id] || ""}
                        onChange={(e) => setAmounts({ ...amounts, [bill.id]: e.target.value })}
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
            <h3 className="mt-8 mb-2 text-sm font-semibold uppercase text-gray-500">Vendor credits to use</h3>
            <table className="w-full text-sm">
              <tbody>
                {credits.map((credit) => (
                  <tr key={credit.id} className="border-b border-gray-100">
                    <td className="py-2">Vendor credit {credit.doc_number || "#" + credit.id}</td>
                    <td className="py-2 text-right">Available {formatMoney(credit.balance, currency)}</td>
                    <td className="w-40 py-2 pl-4">
                      <TextInput
                        type="number"
                        step="0.01"
                        min="0"
                        max={credit.balance}
                        className="text-right"
                        value={creditAmounts[credit.id] || ""}
                        onChange={(e) => setCreditAmounts({ ...creditAmounts, [credit.id]: e.target.value })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <div className="mt-6 ml-auto w-full max-w-xs space-y-1 text-sm">
          <div className="flex justify-between">
            <span>Bills</span>
            <span>{formatMoney(billsTotal, currency)}</span>
          </div>
          {creditsTotal > 0 && (
            <div className="flex justify-between">
              <span>Credits used</span>
              <span>-{formatMoney(creditsTotal, currency)}</span>
            </div>
          )}
          <div className="flex justify-between border-t border-gray-200 pt-2 text-base font-semibold">
            <span>Total payment</span>
            <span>{formatMoney(billsTotal - creditsTotal, currency)}</span>
          </div>
        </div>
      </Card>
      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || billsTotal <= 0}>
          {saving ? "Saving..." : "Save payments"}
        </Button>
      </div>
    </form>
  );
}
