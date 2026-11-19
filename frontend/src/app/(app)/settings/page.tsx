"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, SuccessMessage } from "@/components/ui/Feedback";
import { Field, TextArea, TextInput } from "@/components/ui/FormFields";
import { useAuth } from "@/context/AuthContext";
import { useFormState } from "@/hooks/useFormState";
import { companySettingsService } from "@/services";
import { CompanyInput } from "@/types/inputs";

export default function CompanySettingsPage() {
  const { company, refresh } = useAuth();
  const form = useFormState<CompanyInput>({
    name: company?.name || "",
    email: company?.email || "",
    phone: company?.phone || "",
    address: company?.address || "",
    website: company?.website || "",
    payment_terms_days: company?.payment_terms_days || 30,
  });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await companySettingsService.updateCompany(form.values);
      await refresh();
      setMessage("Company settings saved.");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />
      <Card title="Company">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Company name" required>
            <TextInput required value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Email">
              <TextInput type="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} />
            </Field>
            <Field label="Phone">
              <TextInput value={form.values.phone} onChange={(e) => form.setField("phone", e.target.value)} />
            </Field>
          </div>
          <Field label="Website">
            <TextInput value={form.values.website} onChange={(e) => form.setField("website", e.target.value)} />
          </Field>
          <Field label="Address">
            <TextArea value={form.values.address} onChange={(e) => form.setField("address", e.target.value)} />
          </Field>
          <div className="w-64">
            <Field label="Default invoice terms (days)">
              <TextInput
                type="number"
                min="0"
                max="365"
                value={form.values.payment_terms_days}
                onChange={(e) => form.setField("payment_terms_days", Number(e.target.value))}
              />
            </Field>
          </div>
          <div className="text-sm text-gray-500">Currency: {company?.currency}</div>
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
