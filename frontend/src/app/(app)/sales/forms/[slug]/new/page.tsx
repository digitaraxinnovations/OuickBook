"use client";

import { useParams, useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { emptySalesLine, isFilled, SalesLinesEditor } from "@/components/sales/SalesLinesEditor";
import { emptySalesAmounts, SalesTotals } from "@/components/sales/SalesTotals";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { paymentMethodOptions } from "@/config/options";
import { findFormBySlug } from "@/config/sales-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { todayString } from "@/lib/format";
import { accountService, customerService, inventoryService, productService, salesDocumentService, taxService } from "@/services";
import { SalesAmountsInput, SalesLineInput } from "@/types/inputs";
import { Account, PaymentMethod } from "@/types/models";

/** Accounts that can receive money (sales receipt) or pay a refund. */
function moneyAccountsFor(kind: string, accounts: Account[]): Account[] {
  if (kind === "depositTo") {
    return accounts.filter((account) => account.account_type === "ASSET" && account.system_key !== "accounts_receivable");
  }
  return accounts.filter(
    (account) => account.detail_type === "Bank" || account.detail_type === "Credit Card",
  );
}

/** Create page shared by every sales form type. */
export default function NewSalesFormPage() {
  const params = useParams<{ slug: string }>();
  const form = findFormBySlug(params.slug);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const taxCodes = useLoad(() => taxService.codes(true));

  const [customerId, setCustomerId] = useState("");
  const [docDate, setDocDate] = useState(todayString());
  const [expirationDate, setExpirationDate] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<SalesLineInput[]>([emptySalesLine()]);
  const [amounts, setAmounts] = useState<SalesAmountsInput>(emptySalesAmounts());
  const [moneyAccountId, setMoneyAccountId] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("CASH");
  const [referenceNo, setReferenceNo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const prices = useLoad(() => inventoryService.prices(customerId ? Number(customerId) : null, docDate), [customerId, docDate]);

  if (!form) {
    return <ErrorMessage message="This page does not exist." />;
  }
  if (customers.loading || products.loading || accounts.loading || taxCodes.loading) {
    return <Loading />;
  }
  const config = form;
  const chosenCustomer = (customers.data || []).find((item) => item.id === Number(customerId));

  /** Use the customer's default sales tax rate. */
  function chooseCustomer(value: string) {
    setCustomerId(value);
    const customer = (customers.data || []).find((item) => item.id === Number(value));
    setAmounts({ ...amounts, tax_code_id: customer ? customer.default_tax_code_id : null });
  }
  const handlesMoney = config.moneyAccount !== "none";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const document = await salesDocumentService.create({
        doc_type: config.type,
        customer_id: Number(customerId),
        doc_date: docDate,
        expiration_date: expirationDate,
        memo: memo,
        lines: lines.filter(isFilled),
        tax_code_id: amounts.tax_code_id,
        discount_type: amounts.discount_type,
        discount_value: amounts.discount_value || "0",
        shipping_amount: amounts.shipping_amount || "0",
        money_account_id: moneyAccountId ? Number(moneyAccountId) : null,
        payment_method: handlesMoney ? method : null,
        reference_no: referenceNo,
      });
      router.push("/sales/forms/" + config.slug + "/" + document.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  const moneyAccounts = moneyAccountsFor(config.moneyAccount, accounts.data || []);

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title={"New " + config.title.toLowerCase()} subtitle={config.description} />
      <ErrorMessage message={error} />

      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <Field label="Customer" required>
              <Select
                required
                value={customerId}
                onChange={(e) => chooseCustomer(e.target.value)}
                placeholder="Choose a customer"
                options={(customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }))}
              />
            </Field>
          </div>
          <Field label={config.title + " date"} required>
            <TextInput type="date" required value={docDate} onChange={(e) => setDocDate(e.target.value)} />
          </Field>
          {config.hasExpirationDate && (
            <Field label="Expiration date">
              <TextInput type="date" value={expirationDate} onChange={(e) => setExpirationDate(e.target.value)} />
            </Field>
          )}
          {handlesMoney && (
            <>
              <Field label={config.moneyAccount === "depositTo" ? "Deposit to" : "Refund from"} required={config.moneyAccount === "refundFrom"}>
                <Select
                  required={config.moneyAccount === "refundFrom"}
                  value={moneyAccountId}
                  onChange={(e) => setMoneyAccountId(e.target.value)}
                  placeholder={config.moneyAccount === "depositTo" ? "Undeposited Funds" : "Choose an account"}
                  options={moneyAccounts.map((account) => ({ value: account.id, label: account.full_name }))}
                />
              </Field>
              <Field label="Payment method">
                <Select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} options={paymentMethodOptions} />
              </Field>
              <Field label="Reference no.">
                <TextInput value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
              </Field>
            </>
          )}
        </div>

        <div className="mt-6">
          <SalesLinesEditor lines={lines} onChange={setLines} products={products.data || []} prices={prices.data || []} currency={currency} />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Field label="Message">
            <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="flex justify-end">
            <SalesTotals
              lines={lines}
              amounts={amounts}
              onChange={setAmounts}
              taxCodes={taxCodes.data || []}
              taxExempt={chosenCustomer ? chosenCustomer.tax_exempt : false}
              currency={currency}
            />
          </div>
        </div>
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save " + config.title.toLowerCase()}
        </Button>
      </div>
    </form>
  );
}
