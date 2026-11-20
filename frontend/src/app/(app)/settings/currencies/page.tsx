"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, todayString, toNumber } from "@/lib/format";
import { platformService } from "@/services";

export default function CurrenciesPage() {
  const settings = useLoad(() => platformService.advancedSettings());
  const currencies = useLoad(() => platformService.currencies());
  const rates = useLoad(() => platformService.exchangeRates());
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [rateCode, setRateCode] = useState("");
  const [rateDate, setRateDate] = useState(todayString());
  const [rate, setRate] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (settings.loading || currencies.loading) {
    return <Loading />;
  }
  const home = settings.data?.currency || "";

  async function addCurrency(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await platformService.addCurrency(code.toUpperCase(), name);
      setCode("");
      setName("");
      currencies.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not add the currency.");
    }
  }

  async function saveRate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await platformService.setExchangeRate(rateCode, rateDate, rate);
      setRate("");
      currencies.reload();
      rates.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the rate.");
    }
  }

  async function refreshRates() {
    setError(null);
    try {
      await platformService.refreshExchangeRates();
      currencies.reload();
      rates.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not download rates.");
    }
  }

  if (!settings.data?.multicurrency_enabled) {
    return (
      <Card>
        <p className="text-sm text-gray-600">Turn on multicurrency under Settings → Expenses & advanced to invoice customers in other currencies.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <ErrorMessage message={error} />
      <Card
        title={"Currencies (home currency: " + home + ")"}
        action={
          <Button variant="ghost" onClick={refreshRates}>
            Download today&apos;s rates
          </Button>
        }
      >
        <DataTable
          rows={currencies.data || []}
          rowKey={(row) => row.id}
          emptyText="Add the currencies your customers use."
          columns={[
            { header: "Code", render: (row) => <span className="font-medium">{row.code}</span> },
            { header: "Name", render: (row) => row.name },
            { header: "Latest rate", align: "right", render: (row) => (row.latest_rate ? "1 " + row.code + " = " + toNumber(row.latest_rate) + " " + home : "No rate yet") },
            { header: "Rate date", render: (row) => (row.latest_rate_date ? formatDate(row.latest_rate_date) : "") },
          ]}
        />
        <form onSubmit={addCurrency} className="mt-4 flex flex-wrap items-end gap-3">
          <div className="w-28">
            <Field label="Code">
              <TextInput required maxLength={3} value={code} onChange={(e) => setCode(e.target.value)} placeholder="EUR" />
            </Field>
          </div>
          <div className="w-60">
            <Field label="Name">
              <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="Euro" />
            </Field>
          </div>
          <Button type="submit" variant="secondary">
            Add currency
          </Button>
        </form>
      </Card>

      <Card title="Exchange rates">
        <form onSubmit={saveRate} className="mb-4 flex flex-wrap items-end gap-3">
          <div className="w-32">
            <Field label="Currency">
              <Select required value={rateCode} onChange={(e) => setRateCode(e.target.value)} placeholder="Choose" options={(currencies.data || []).map((item) => ({ value: item.code, label: item.code }))} />
            </Field>
          </div>
          <div className="w-44">
            <Field label="Date">
              <TextInput type="date" required value={rateDate} onChange={(e) => setRateDate(e.target.value)} />
            </Field>
          </div>
          <div className="w-44">
            <Field label={"1 unit = how many " + home}>
              <TextInput type="number" step="0.00000001" min="0" required value={rate} onChange={(e) => setRate(e.target.value)} />
            </Field>
          </div>
          <Button type="submit" variant="secondary">
            Save rate
          </Button>
        </form>
        <DataTable
          rows={rates.data || []}
          rowKey={(row) => row.id}
          emptyText="No rates yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.rate_date) },
            { header: "Currency", render: (row) => row.currency_code },
            { header: "Rate", align: "right", render: (row) => toNumber(row.rate) },
          ]}
        />
      </Card>
    </div>
  );
}
