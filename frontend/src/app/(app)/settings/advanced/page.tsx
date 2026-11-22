"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { useAuth } from "@/context/AuthContext";
import { SimulatedBadge } from "@/components/ui/SimulatedBadge";
import { useIntegrations } from "@/hooks/useIntegrations";
import { useLoad } from "@/hooks/useLoad";
import { platformService } from "@/services";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export default function AdvancedSettingsPage() {
  const { refresh } = useAuth();
  const settings = useLoad(() => platformService.advancedSettings());
  const integrations = useIntegrations();
  const [billTerms, setBillTerms] = useState("30");
  const [fiscalMonth, setFiscalMonth] = useState("1");
  const [method, setMethod] = useState("ACCRUAL");
  const [closingDate, setClosingDate] = useState("");
  const [closingPassword, setClosingPassword] = useState("");
  const [removePassword, setRemovePassword] = useState(false);
  const [multicurrency, setMulticurrency] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings.data) {
      setBillTerms(String(settings.data.bill_terms_days));
      setFiscalMonth(String(settings.data.fiscal_year_start_month));
      setMethod(settings.data.accounting_method);
      setClosingDate(settings.data.closing_date || "");
      setMulticurrency(settings.data.multicurrency_enabled);
    }
  }, [settings.data]);

  if (settings.loading || !settings.data) {
    return <Loading />;
  }
  const current = settings.data;

  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (multicurrency && !current.multicurrency_enabled && !window.confirm("Multicurrency cannot be turned off again. Turn it on?")) {
      return;
    }
    try {
      await platformService.saveAdvancedSettings({
        bill_terms_days: Number(billTerms),
        fiscal_year_start_month: Number(fiscalMonth),
        accounting_method: method,
        closing_date: closingDate || null,
        closing_password: closingPassword || null,
        remove_closing_password: removePassword,
        multicurrency_enabled: multicurrency,
      });
      setClosingPassword("");
      setRemovePassword(false);
      setMessage("Settings saved.");
      settings.reload();
      refresh();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={save} className="max-w-3xl space-y-6">
      <ErrorMessage message={error} />
      {message && <div className="rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</div>}

      <Card title="Expenses">
        <div className="w-60">
          <Field label="Bills are due after (days)">
            <TextInput type="number" min="0" max="365" value={billTerms} onChange={(e) => setBillTerms(e.target.value)} />
          </Field>
        </div>
        <p className="mt-2 text-sm text-gray-500">Used when a bill has no terms of its own and the vendor has none.</p>
      </Card>

      <Card title="Payments">
        <p className="text-sm text-gray-600">
          {integrations?.payments.enabled
            ? "Customers can pay invoices online from the link you send them (payment service: " + integrations.payments.provider + ")."
            : "Online card and bank payments on invoices need a payment service. None is connected (PAYMENT_PROVIDER=none in the settings file), so customers pay you the usual way and you record the payment."}
          {integrations?.payments.simulated && <SimulatedBadge title="Simulated: the checkout page is a pretend one and no money moves." />}
        </p>
      </Card>

      <Card title="Accounting">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="First month of the fiscal year">
            <Select value={fiscalMonth} onChange={(e) => setFiscalMonth(e.target.value)} options={MONTHS.map((name, index) => ({ value: index + 1, label: name }))} />
          </Field>
          <Field label="Accounting method reports start with">
            <Select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              options={[
                { value: "ACCRUAL", label: "Accrual (when invoiced or billed)" },
                { value: "CASH", label: "Cash (when paid)" },
              ]}
            />
          </Field>
        </div>
      </Card>

      <Card title="Close the books">
        <p className="mb-4 text-sm text-gray-600">
          Nothing dated on or before the closing date can be added or changed without the closing password (for example after you file your taxes).
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Closing date">
            <TextInput type="date" value={closingDate} onChange={(e) => setClosingDate(e.target.value)} />
          </Field>
          <Field label={current.has_closing_password ? "New closing password (empty = keep)" : "Closing password"}>
            <TextInput type="password" value={closingPassword} onChange={(e) => setClosingPassword(e.target.value)} autoComplete="new-password" />
          </Field>
        </div>
        {current.has_closing_password && (
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={removePassword} onChange={(e) => setRemovePassword(e.target.checked)} />
            Remove the closing password
          </label>
        )}
      </Card>

      <Card title="Currency">
        <p className="mb-3 text-sm text-gray-600">Home currency: {current.currency}</p>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={multicurrency} disabled={current.multicurrency_enabled} onChange={(e) => setMulticurrency(e.target.checked)} />
          Multicurrency (customers can be invoiced in other currencies)
        </label>
      </Card>

      <Button type="submit">Save</Button>
    </form>
  );
}
