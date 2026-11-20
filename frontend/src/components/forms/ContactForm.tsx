"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { useFormState } from "@/hooks/useFormState";
import { ContactInput } from "@/types/inputs";
import { Contact, PaymentTerm } from "@/types/models";

interface ContactExtras {
  terms_id?: number | null;
  track_1099?: boolean;
  tax_id?: string | null;
}

export function contactToInput(contact: (Contact & ContactExtras) | null): ContactInput {
  return {
    display_name: contact?.display_name || "",
    company_name: contact?.company_name || "",
    email: contact?.email || "",
    phone: contact?.phone || "",
    address: contact?.address || "",
    notes: contact?.notes || "",
    is_active: contact ? contact.is_active : true,
    terms_id: contact?.terms_id ?? null,
    track_1099: contact?.track_1099 ?? false,
    tax_id: contact?.tax_id || "",
  };
}

interface ContactFormProps {
  initial: (Contact & ContactExtras) | null;
  /** Shows the default payment terms field. */
  terms?: PaymentTerm[];
  /** Vendors only: show the 1099 contractor fields. */
  vendorFields?: boolean;
  onSave: (input: ContactInput) => Promise<void>;
  onCancel: () => void;
}

/** Form used for both customers and vendors. */
export function ContactForm({ initial, terms, vendorFields, onSave, onCancel }: ContactFormProps) {
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
      {terms && (
        <Field label="Payment terms">
          <Select
            value={form.values.terms_id ?? ""}
            onChange={(e) => form.setField("terms_id", e.target.value ? Number(e.target.value) : null)}
            placeholder="Company default"
            options={terms.filter((term) => term.is_active).map((term) => ({ value: term.id, label: term.name }))}
          />
        </Field>
      )}
      {vendorFields && (
        <div className="grid grid-cols-2 items-end gap-4">
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input type="checkbox" checked={form.values.track_1099 || false} onChange={(e) => form.setField("track_1099", e.target.checked)} />
            Track payments for 1099
          </label>
          <Field label="Tax ID (SSN / EIN)">
            <TextInput value={form.values.tax_id || ""} onChange={(e) => form.setField("tax_id", e.target.value)} />
          </Field>
        </div>
      )}
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
