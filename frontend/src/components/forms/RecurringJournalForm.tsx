"use client";

import { FormEvent, useState } from "react";
import {
  emptyJournalLine,
  JournalLinesEditor,
  journalLinesToInput,
  JournalLineState,
  journalTotals,
} from "@/components/forms/JournalLinesEditor";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, SelectOption, TextInput } from "@/components/ui/FormFields";
import { todayString } from "@/lib/format";
import { RecurringScheduleInput } from "@/types/inputs";
import { RecurringFrequency, RecurringSchedule } from "@/types/models";

export const frequencyOptions = [
  { value: "DAILY", label: "Day(s)" },
  { value: "WEEKLY", label: "Week(s)" },
  { value: "MONTHLY", label: "Month(s)" },
  { value: "YEARLY", label: "Year(s)" },
];

interface SavedLine {
  account_id: number;
  description: string | null;
  debit: string;
  credit: string;
}

/** Turns a saved template back into editor rows. */
function templateToLines(schedule: RecurringSchedule | null): JournalLineState[] {
  if (!schedule) {
    return [emptyJournalLine(), emptyJournalLine()];
  }
  const saved = (schedule.template.lines || []) as SavedLine[];
  return saved.map((line) => ({
    account_id: String(line.account_id),
    description: line.description || "",
    debit: Number(line.debit) > 0 ? String(line.debit) : "",
    credit: Number(line.credit) > 0 ? String(line.credit) : "",
  }));
}

interface RecurringJournalFormProps {
  initial: RecurringSchedule | null;
  accountOptions: SelectOption[];
  currency?: string;
  onSave: (input: RecurringScheduleInput) => Promise<void>;
  onCancel: () => void;
}

export function RecurringJournalForm({ initial, accountOptions, currency, onSave, onCancel }: RecurringJournalFormProps) {
  const [name, setName] = useState(initial?.name || "");
  const [frequency, setFrequency] = useState<RecurringFrequency>(initial?.frequency || "MONTHLY");
  const [repeatEvery, setRepeatEvery] = useState(initial?.interval || 1);
  const [startDate, setStartDate] = useState(initial?.start_date || todayString());
  const [endDate, setEndDate] = useState(initial?.end_date || "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [memo, setMemo] = useState(initial ? String(initial.template.memo || "") : "");
  const [lines, setLines] = useState<JournalLineState[]>(templateToLines(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name,
        transaction_type: "JOURNAL_ENTRY",
        frequency: frequency,
        interval: repeatEvery,
        start_date: startDate,
        end_date: endDate,
        is_active: isActive,
        template: { memo: memo, lines: journalLinesToInput(lines) },
      });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Template name" required>
          <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Monthly depreciation" />
        </Field>
        <Field label="Memo">
          <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        <Field label="Every" required>
          <TextInput type="number" min="1" max="99" required value={repeatEvery} onChange={(e) => setRepeatEvery(Number(e.target.value))} />
        </Field>
        <Field label="Period">
          <Select value={frequency} onChange={(e) => setFrequency(e.target.value as RecurringFrequency)} options={frequencyOptions} />
        </Field>
        <Field label="Start date" required>
          <TextInput type="date" required disabled={initial !== null && initial.run_count > 0} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="End date">
          <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
      </div>

      <JournalLinesEditor lines={lines} onChange={setLines} accountOptions={accountOptions} currency={currency} />

      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active (uncheck to pause)
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !journalTotals(lines).isBalanced}>
          {saving ? "Saving..." : "Save template"}
        </Button>
      </div>
    </form>
  );
}
