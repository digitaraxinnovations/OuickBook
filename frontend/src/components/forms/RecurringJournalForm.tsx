"use client";

import { FormEvent, useState } from "react";
import {
  emptyJournalLine,
  JournalLinesEditor,
  journalLinesToInput,
  JournalLineState,
  journalTotals,
} from "@/components/forms/JournalLinesEditor";
import { ScheduleFields, ScheduleValues } from "@/components/forms/ScheduleFields";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, SelectOption, TextInput } from "@/components/ui/FormFields";
import { todayString } from "@/lib/format";
import { RecurringScheduleInput } from "@/types/inputs";
import { RecurringSchedule } from "@/types/models";

interface SavedLine {
  account_id: number;
  description: string | null;
  debit: string;
  credit: string;
}

export function scheduleToValues(schedule: RecurringSchedule | null): ScheduleValues {
  return {
    name: schedule?.name || "",
    frequency: schedule?.frequency || "MONTHLY",
    interval: schedule?.interval || 1,
    start_date: schedule?.start_date || todayString(),
    end_date: schedule?.end_date || "",
    is_active: schedule ? schedule.is_active : true,
  };
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
  const [schedule, setSchedule] = useState<ScheduleValues>(scheduleToValues(initial));
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
        ...schedule,
        transaction_type: "JOURNAL_ENTRY",
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
      <ScheduleFields values={schedule} onChange={setSchedule} startDateLocked={initial !== null && initial.run_count > 0} />
      <Field label="Memo">
        <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
      </Field>
      <JournalLinesEditor lines={lines} onChange={setLines} accountOptions={accountOptions} currency={currency} />
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={schedule.is_active} onChange={(e) => setSchedule({ ...schedule, is_active: e.target.checked })} />
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
