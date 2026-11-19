"use client";

import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { RecurringFrequency } from "@/types/models";

export const frequencyOptions = [
  { value: "DAILY", label: "Day(s)" },
  { value: "WEEKLY", label: "Week(s)" },
  { value: "MONTHLY", label: "Month(s)" },
  { value: "YEARLY", label: "Year(s)" },
];

export interface ScheduleValues {
  name: string;
  frequency: RecurringFrequency;
  interval: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

interface ScheduleFieldsProps {
  values: ScheduleValues;
  onChange: (values: ScheduleValues) => void;
  /** Start date cannot change after the schedule has run. */
  startDateLocked: boolean;
}

/** Name and "every N periods from ... to ..." fields shared by all recurring templates. */
export function ScheduleFields({ values, onChange, startDateLocked }: ScheduleFieldsProps) {
  function update(changes: Partial<ScheduleValues>) {
    onChange({ ...values, ...changes });
  }

  return (
    <div className="space-y-4">
      <Field label="Template name" required>
        <TextInput required value={values.name} onChange={(e) => update({ name: e.target.value })} placeholder="e.g. Monthly retainer" />
      </Field>
      <div className="grid gap-4 md:grid-cols-4">
        <Field label="Every" required>
          <TextInput type="number" min="1" max="99" required value={values.interval} onChange={(e) => update({ interval: Number(e.target.value) })} />
        </Field>
        <Field label="Period">
          <Select value={values.frequency} onChange={(e) => update({ frequency: e.target.value as RecurringFrequency })} options={frequencyOptions} />
        </Field>
        <Field label="Start date" required>
          <TextInput type="date" required disabled={startDateLocked} value={values.start_date} onChange={(e) => update({ start_date: e.target.value })} />
        </Field>
        <Field label="End date">
          <TextInput type="date" value={values.end_date} onChange={(e) => update({ end_date: e.target.value })} />
        </Field>
      </div>
    </div>
  );
}
