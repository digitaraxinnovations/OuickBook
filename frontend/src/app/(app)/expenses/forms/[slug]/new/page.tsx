"use client";

import { useParams, useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { emptyPurchaseLine, PurchaseLinesEditor, purchaseLinesTotal } from "@/components/purchases/PurchaseLinesEditor";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { findPurchaseFormBySlug } from "@/config/purchase-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney, todayString } from "@/lib/format";
import { accountService, customerService, productService, purchaseService, termsService, vendorService } from "@/services";
import { PurchaseLineInput } from "@/types/inputs";

export default function NewPurchaseFormPage() {
  const params = useParams<{ slug: string }>();
  const form = findPurchaseFormBySlug(params.slug);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const terms = useLoad(() => termsService.list());
  const products = useLoad(() => productService.list({ active_only: true }));

  const [vendorId, setVendorId] = useState("");
  const [docDate, setDocDate] = useState(todayString());
  const [dueDate, setDueDate] = useState("");
  const [termsId, setTermsId] = useState("");
  const [docNumber, setDocNumber] = useState("");
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<PurchaseLineInput[]>([emptyPurchaseLine()]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!form) {
    return <ErrorMessage message="This page does not exist." />;
  }
  if (vendors.loading || accounts.loading || customers.loading || terms.loading || products.loading) {
    return <Loading />;
  }
  const config = form;

  const allAccounts = accounts.data || [];
  const expenseAccounts = allAccounts.filter((account) => account.account_type === "EXPENSE");
  const otherAccounts = allAccounts.filter(
    (account) => account.account_type !== "EXPENSE" && account.system_key !== "accounts_payable",
  );
  const categoryOptions = [...expenseAccounts, ...otherAccounts].map((account) => ({ value: account.id, label: account.full_name }));
  const customerOptions = (customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }));

  function chooseVendor(value: string) {
    setVendorId(value);
    const vendor = (vendors.data || []).find((item) => item.id === Number(value));
    setTermsId(vendor && vendor.terms_id ? String(vendor.terms_id) : "");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const document = await purchaseService.create({
        doc_type: config.type,
        vendor_id: Number(vendorId),
        doc_date: docDate,
        due_date: dueDate,
        terms_id: termsId ? Number(termsId) : null,
        doc_number: docNumber,
        memo: memo,
        lines: lines,
      });
      router.push("/expenses/forms/" + config.slug + "/" + document.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title={"New " + config.title.toLowerCase()} subtitle={config.description} />
      <ErrorMessage message={error} />
      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <Field label="Vendor" required>
              <Select
                required
                value={vendorId}
                onChange={(e) => chooseVendor(e.target.value)}
                placeholder="Choose a vendor"
                options={(vendors.data || []).map((vendor) => ({ value: vendor.id, label: vendor.display_name }))}
              />
            </Field>
          </div>
          <Field label={config.title + " date"} required>
            <TextInput type="date" required value={docDate} onChange={(e) => setDocDate(e.target.value)} />
          </Field>
          {config.numberLabel && (
            <Field label={config.numberLabel}>
              <TextInput value={docNumber} onChange={(e) => setDocNumber(e.target.value)} />
            </Field>
          )}
          {config.hasDueDate && (
            <>
              <Field label="Terms">
                <Select
                  value={termsId}
                  onChange={(e) => setTermsId(e.target.value)}
                  placeholder={"Company default (" + company?.payment_terms_days + " days)"}
                  options={(terms.data || []).filter((term) => term.is_active).map((term) => ({ value: term.id, label: term.name }))}
                />
              </Field>
              <Field label="Due date (empty = from terms)">
                <TextInput type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </Field>
            </>
          )}
        </div>

        <div className="mt-6">
          <PurchaseLinesEditor
            lines={lines}
            onChange={setLines}
            categoryOptions={categoryOptions}
            customerOptions={customerOptions}
            products={products.data || []}
            currency={currency}
          />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Field label="Memo">
            <TextArea value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
          <div className="text-right">
            <div className="text-sm text-gray-500">Total</div>
            <div className="text-3xl font-semibold">{formatMoney(purchaseLinesTotal(lines), currency)}</div>
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
