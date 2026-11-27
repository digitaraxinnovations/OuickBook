"use client";

import Link from "next/link";
import { useState } from "react";
import { BalanceChart, BalanceSeries } from "@/components/charts/BalanceChart";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { dailyBalances, emptyScenario, isChanged, lowestDay, Scenario, scenarioItems } from "@/lib/forecast-scenarios";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { reportService } from "@/services";
import { Forecast } from "@/types/models";

const EXPECTED_COLOR = "#2a78d6";
const WHAT_IF_COLOR = "#eb6834";

export default function ForecastPage() {
  const forecast = useLoad(() => reportService.getForecast());

  if (forecast.loading) {
    return <Loading />;
  }
  if (!forecast.data) {
    return <ErrorMessage message={forecast.error} />;
  }
  return <ForecastView forecast={forecast.data} />;
}

function Figure({ label, value, note, bad }: { label: string; value: string; note?: string; bad?: boolean }) {
  return (
    <Card>
      <div className="text-xs font-semibold uppercase text-gray-500">{label}</div>
      <div className={"mt-1 text-2xl font-semibold " + (bad ? "text-red-600" : "text-gray-900")}>{value}</div>
      {note && <div className="mt-1 text-xs text-gray-500">{note}</div>}
    </Card>
  );
}

function ForecastView({ forecast }: { forecast: Forecast }) {
  const { company } = useAuth();
  const currency = company?.currency;
  const [scenario, setScenario] = useState<Scenario>(() => emptyScenario(forecast.start_date));

  const changed = isChanged(scenario);
  const items = changed ? scenarioItems(forecast, scenario) : forecast.items;
  const days = changed ? dailyBalances(forecast, items) : forecast.days;
  const limit = toNumber(forecast.low_balance_limit);
  const lowest = lowestDay(days);
  const firstLow = days.find((day) => toNumber(day.balance) < limit);
  const last = days[days.length - 1];

  const series: BalanceSeries[] = [{ label: "Expected", color: EXPECTED_COLOR, days: forecast.days }];
  if (changed) {
    series.push({ label: "What if", color: WHAT_IF_COLOR, days });
  }

  const customers = new Map<number, string>();
  for (const item of forecast.items) {
    if (item.customer_id !== null && toNumber(item.amount) > 0) {
      customers.set(item.customer_id, item.customer_name || "Customer");
    }
  }

  const balanceOn = new Map(days.map((day) => [day.date, day.balance]));
  const rows = items.map((item, index) => ({ ...item, key: index, lastOfDay: items[index + 1]?.date !== item.date }));

  function change(values: Partial<Scenario>) {
    setScenario({ ...scenario, ...values });
  }

  return (
    <div>
      <PageHeader
        title="Cash flow forecast"
        subtitle={"Expected bank balance from " + formatDate(forecast.start_date) + " to " + formatDate(forecast.end_date) + ". An estimate, not a guarantee."}
      />

      {firstLow && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <strong>Warning{changed ? " (what if)" : ""}:</strong> on {formatDate(firstLow.date)} the balance falls to {formatMoney(firstLow.balance, currency)}.
        </div>
      )}
      {forecast.notes.map((note) => (
        <div key={note} className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {note}
        </div>
      ))}

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Figure label="In the bank today" value={formatMoney(forecast.starting_balance, currency)} />
        <Figure label="Lowest point" value={formatMoney(lowest.balance, currency)} note={formatDate(lowest.date)} bad={toNumber(lowest.balance) < limit} />
        <Figure label={"On " + formatDate(forecast.end_date)} value={formatMoney(last.balance, currency)} bad={toNumber(last.balance) < limit} />
      </div>

      <Card className="mb-6">
        <BalanceChart series={series} limit={limit} currency={currency} />
      </Card>

      <Card title="What if..." className="mb-6" action={changed ? <Button variant="ghost" onClick={() => setScenario(emptyScenario(forecast.start_date))}>Clear</Button> : undefined}>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-3">
            <Field label="A customer pays later">
              <Select
                value={scenario.delayCustomerId === null ? "" : String(scenario.delayCustomerId)}
                onChange={(e) => change({ delayCustomerId: e.target.value ? Number(e.target.value) : null })}
                placeholder="Choose a customer"
                options={[...customers].map(([value, label]) => ({ value, label }))}
              />
            </Field>
            <Field label="Days later">
              <TextInput type="number" min="0" value={scenario.delayDays} onChange={(e) => change({ delayDays: Number(e.target.value) })} />
            </Field>
          </div>
          <div className="space-y-3">
            <Field label="A one-time purchase">
              <TextInput type="number" min="0" step="0.01" value={scenario.purchaseAmount || ""} placeholder="Amount" onChange={(e) => change({ purchaseAmount: Number(e.target.value) })} />
            </Field>
            <Field label="Paid on">
              <TextInput type="date" min={forecast.start_date} max={forecast.end_date} value={scenario.purchaseDate} onChange={(e) => change({ purchaseDate: e.target.value })} />
            </Field>
          </div>
          <div className="space-y-3">
            <Field label="A new monthly cost (e.g. a hire)">
              <TextInput type="number" min="0" step="0.01" value={scenario.monthlyAmount || ""} placeholder="Amount per month" onChange={(e) => change({ monthlyAmount: Number(e.target.value) })} />
            </Field>
            <Field label="Starting">
              <TextInput type="date" min={forecast.start_date} max={forecast.end_date} value={scenario.monthlyStart} onChange={(e) => change({ monthlyStart: e.target.value })} />
            </Field>
          </div>
        </div>
        <p className="mt-3 text-xs text-gray-500">Trying something here changes only this screen. Your books are not touched.</p>
      </Card>

      <h2 className="mb-3 text-lg font-semibold">Expected money in and out</h2>
      <DataTable
        rows={rows}
        rowKey={(row) => row.key}
        emptyText="Nothing expected yet. Open invoices, bills, payroll and recurring transactions appear here."
        columns={[
          { header: "Date", render: (row) => formatDate(row.date) },
          { header: "Type", render: (row) => row.type },
          {
            header: "What",
            render: (row) =>
              row.link ? (
                <Link className="text-brand-700 hover:underline" href={row.link}>
                  {row.description}
                </Link>
              ) : (
                row.description
              ),
          },
          { header: "Money in", align: "right", render: (row) => (toNumber(row.amount) > 0 ? formatMoney(row.amount, currency) : "") },
          { header: "Money out", align: "right", render: (row) => (toNumber(row.amount) < 0 ? formatMoney(-toNumber(row.amount), currency) : "") },
          { header: "Balance", align: "right", render: (row) => (row.lastOfDay ? formatMoney(balanceOn.get(row.date), currency) : "") },
        ]}
      />
      <p className="mt-3 text-xs text-gray-500">
        Not included: future one-off sales, credit card payoff, and payroll taxes or deductions already waiting to be paid. Invoices from recurring
        schedules are before sales tax. Customers who usually pay late are expected that much later.
      </p>
    </div>
  );
}
