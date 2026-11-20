"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { trackingService } from "@/services";
import { Customer, Project } from "@/types/models";

export const projectStatusOptions = [
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELED", label: "Canceled" },
];

export function ProjectForm({ initial, customers, onSaved, onCancel }: {
  initial: Project | null;
  customers: Customer[];
  onSaved: (project: Project) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [customerId, setCustomerId] = useState(initial ? String(initial.customer_id) : "");
  const [status, setStatus] = useState<string>(initial ? initial.status : "IN_PROGRESS");
  const [startDate, setStartDate] = useState(initial?.start_date || "");
  const [endDate, setEndDate] = useState(initial?.end_date || "");
  const [description, setDescription] = useState(initial?.description || "");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const project = await trackingService.saveProject(
        {
          name: name,
          customer_id: Number(customerId),
          status: status,
          start_date: startDate || null,
          end_date: endDate || null,
          description: description,
        },
        initial?.id,
      );
      onSaved(project);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Project name" required>
          <TextInput required value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Customer" required>
          <Select
            required
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Choose a customer"
            options={customers.map((customer) => ({ value: customer.id, label: customer.display_name }))}
          />
        </Field>
        <Field label="Start date">
          <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="End date">
          <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
        {initial && (
          <Field label="Status">
            <Select value={status} onChange={(e) => setStatus(e.target.value)} options={projectStatusOptions} />
          </Field>
        )}
      </div>
      <Field label="Notes">
        <TextArea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}
