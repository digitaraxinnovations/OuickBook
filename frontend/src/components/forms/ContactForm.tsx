"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, TextArea, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { ContactInput } from "@/types/inputs";
import { Contact } from "@/types/models";

export function contactToInput(contact: Contact | null): ContactInput {
  return {
    display_name: contact?.display_name || "",
    company_name: contact?.company_name || "",
    email: contact?.email || "",
    phone: contact?.phone || "",
    address: contact?.address || "",
    notes: contact?.notes || "",
    is_active: contact ? contact.is_active : true,
  };
}

interface ContactFormProps {
  initial: Contact | null;
  onSave: (input: ContactInput) => Promise<void>;
  onCancel: () => void;
}

/** Form used for both customers and vendors. */
export function ContactForm({ initial, onSave, onCancel }: ContactFormProps) {
  const form = useFormState<ContactInput>(contactToInput(initial));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(form.values);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <Field label="Display name" required>
        <TextInput required value={form.values.display_name} onChange={(e) => form.setField("display_name", e.target.value)} />
      </Field>
      <Field label="Company name">
        <TextInput value={form.values.company_name} onChange={(e) => form.setField("company_name", e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Email">
          <TextInput type="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} />
        </Field>
        <Field label="Phone">
          <TextInput value={form.values.phone} onChange={(e) => form.setField("phone", e.target.value)} />
        </Field>
      </div>
      <Field label="Address">
        <TextArea rows={2} value={form.values.address} onChange={(e) => form.setField("address", e.target.value)} />
      </Field>
      <Field label="Notes">
        <TextArea rows={2} value={form.values.notes} onChange={(e) => form.setField("notes", e.target.value)} />
      </Field>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.values.is_active} onChange={(e) => form.setField("is_active", e.target.checked)} />
          Active
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
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
