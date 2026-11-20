"use client";

import { FormEvent, ReactNode, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { todayString, toNumber } from "@/lib/format";
import { taxService } from "@/services";
import { TaxAgency, TaxCode, TaxRate } from "@/types/models";

/** Save / cancel buttons and error message shared by the three forms. */
function FormShell({ onSubmit, onCancel, error, saving, children }: {
  onSubmit: () => Promise<void>;
  onCancel: () => void;
  error: string | null;
  saving: boolean;
  children: ReactNode;
}) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      {children}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}

/** Runs a save and keeps track of the saving flag and error message. */
function useSaver(onSaved: () => void) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function run(save: () => Promise<unknown>) {
    setSaving(true);
    setError(null);
    try {
      await save();
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return { error, saving, run };
}

interface FormProps<T> {
  initial: T | null;
  onSaved: () => void;
  onCancel: () => void;
}

// ---------- agency ----------

export function AgencyForm({ initial, onSaved, onCancel }: FormProps<TaxAgency>) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [frequency, setFrequency] = useState(initial ? initial.filing_frequency : "QUARTERLY");
  const [startDate, setStartDate] = useState(initial ? initial.start_date : todayString().slice(0, 8) + "01");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const saver = useSaver(onSaved);

  async function save() {
    const input = { name: name, filing_frequency: frequency, start_date: startDate, is_active: isActive };
    await saver.run(() => taxService.saveAgency(input, initial?.id));
  }

  return (
    <FormShell onSubmit={save} onCancel={onCancel} error={saver.error} saving={saver.saving}>
      <Field label="Agency name" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. State Department of Revenue" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Filing frequency" required>
          <Select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as TaxAgency["filing_frequency"])}
            options={[
              { value: "MONTHLY", label: "Monthly" },
              { value: "QUARTERLY", label: "Quarterly" },
              { value: "YEARLY", label: "Yearly" },
            ]}
          />
        </Field>
        <Field label="Start of first filing period" required>
          <TextInput type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
      {!initial && <p className="text-xs text-gray-500">A liability account for this agency is created under Sales Tax Payable.</p>}
    </FormShell>
  );
}

// ---------- rate ----------

interface RateFormProps extends FormProps<TaxRate> {
  agencies: TaxAgency[];
}

export function RateForm({ initial, agencies, onSaved, onCancel }: RateFormProps) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [agencyId, setAgencyId] = useState(initial ? String(initial.agency_id) : agencies.length === 1 ? String(agencies[0].id) : "");
  const [rate, setRate] = useState(initial ? String(toNumber(initial.rate)) : "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [createCode, setCreateCode] = useState(true);
  const saver = useSaver(onSaved);

  async function save() {
    const input = { name: name, agency_id: Number(agencyId), rate: rate, is_active: isActive, create_code: initial ? false : createCode };
    await saver.run(() => taxService.saveRate(input, initial?.id));
  }

  return (
    <FormShell onSubmit={save} onCancel={onCancel} error={saver.error} saving={saver.saving}>
      <Field label="Rate name" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. State tax" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Agency" required>
          <Select required value={agencyId} onChange={(e) => setAgencyId(e.target.value)} placeholder="Choose" options={agencies.map((agency) => ({ value: agency.id, label: agency.name }))} />
        </Field>
        <Field label="Rate (%)" required>
          <TextInput type="number" step="0.0001" min="0" max="100" required value={rate} onChange={(e) => setRate(e.target.value)} />
        </Field>
      </div>
      {initial ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      ) : (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={createCode} onChange={(e) => setCreateCode(e.target.checked)} />
          Also add it to the list you pick from on invoices
        </label>
      )}
    </FormShell>
  );
}

// ---------- combined code ----------

interface CodeFormProps extends FormProps<TaxCode> {
  rates: TaxRate[];
}

export function CodeForm({ initial, rates, onSaved, onCancel }: CodeFormProps) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [rateIds, setRateIds] = useState<number[]>(initial ? initial.components.map((component) => component.tax_rate_id) : []);
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const saver = useSaver(onSaved);

  function toggleRate(id: number) {
    if (rateIds.includes(id)) {
      setRateIds(rateIds.filter((item) => item !== id));
    } else {
      setRateIds([...rateIds, id]);
    }
  }

  let total = 0;
  for (const rate of rates) {
    if (rateIds.includes(rate.id)) {
      total += toNumber(rate.rate);
    }
  }

  async function save() {
    const input = { name: name, rate_ids: rateIds, is_active: isActive };
    await saver.run(() => taxService.saveCode(input, initial?.id));
  }

  return (
    <FormShell onSubmit={save} onCancel={onCancel} error={saver.error} saving={saver.saving}>
      <Field label="Name shown on invoices" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Springfield combined" />
      </Field>
      <div>
        <div className="mb-1 text-sm font-medium text-gray-700">Rates to add together</div>
        <div className="space-y-1 rounded-md border border-gray-200 p-3">
          {rates.map((rate) => (
            <label key={rate.id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={rateIds.includes(rate.id)} onChange={() => toggleRate(rate.id)} />
              {rate.name}
              <span className="ml-auto text-gray-500">{toNumber(rate.rate)}%</span>
            </label>
          ))}
        </div>
        <div className="mt-2 text-right text-sm">
          Combined rate: <strong>{Math.round(total * 10000) / 10000}%</strong>
        </div>
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
    </FormShell>
  );
}
