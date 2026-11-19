"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading, SuccessMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea, TextInput } from "@/components/ui/FormFields";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { readFileAsBase64 } from "@/lib/files";
import { companySettingsService } from "@/services";
import { SalesSettings } from "@/types/models";

const templateOptions = [
  { value: "classic", label: "Classic - colored title" },
  { value: "modern", label: "Modern - colored banner" },
  { value: "simple", label: "Simple - black and white" },
];

export default function SalesSettingsPage() {
  const { refresh } = useAuth();
  const loaded = useLoad(() => companySettingsService.getSalesSettings());
  const logo = useLoad(() => companySettingsService.getLogo());
  const [settings, setSettings] = useState<SalesSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (loaded.data) {
      setSettings(loaded.data);
    }
  }, [loaded.data]);

  if (!settings) {
    return loaded.error ? <ErrorMessage message={loaded.error} /> : <Loading />;
  }

  function update(changes: Partial<SalesSettings>) {
    setSettings({ ...(settings as SalesSettings), ...changes });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await companySettingsService.updateSalesSettings(settings as SalesSettings);
      await refresh();
      setMessage("Sales settings saved.");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  async function uploadLogo(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setError(null);
    try {
      const base64 = await readFileAsBase64(file);
      await companySettingsService.uploadLogo(file.type, base64);
      logo.reload();
      setMessage("Logo uploaded.");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not upload the logo.");
    }
  }

  async function removeLogo() {
    await companySettingsService.removeLogo();
    logo.reload();
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />

      <Card title="Invoice look">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <Field label="Template">
              <Select value={settings.invoice_template} onChange={(e) => update({ invoice_template: e.target.value })} options={templateOptions} />
            </Field>
            <Field label="Accent color">
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={settings.invoice_accent_color}
                  onChange={(e) => update({ invoice_accent_color: e.target.value })}
                  className="h-10 w-16 cursor-pointer rounded border border-gray-300"
                />
                <span className="text-sm text-gray-600">{settings.invoice_accent_color}</span>
              </div>
            </Field>
            <Field label="Footer message (printed on every invoice)">
              <TextArea value={settings.invoice_footer || ""} onChange={(e) => update({ invoice_footer: e.target.value })} />
            </Field>
          </div>
          <div>
            <div className="mb-1 text-sm font-medium text-gray-700">Logo (PNG or JPG)</div>
            <div className="flex h-32 items-center justify-center rounded-md border border-dashed border-gray-300 bg-gray-50">
              {logo.data?.data_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logo.data.data_url} alt="Company logo" className="max-h-28 max-w-full" />
              ) : (
                <span className="text-sm text-gray-400">No logo yet</span>
              )}
            </div>
            <div className="mt-2 flex items-center gap-2">
              <input type="file" accept="image/png,image/jpeg" onChange={uploadLogo} className="text-sm" />
              {logo.data?.data_url && (
                <Button type="button" variant="ghost" onClick={removeLogo}>
                  Remove
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card title="Late fees">
        <label className="mb-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={settings.late_fee_enabled} onChange={(e) => update({ late_fee_enabled: e.target.checked })} />
          Add a late fee to overdue invoices (once per invoice)
        </label>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Fee type">
            <Select
              value={settings.late_fee_type}
              onChange={(e) => update({ late_fee_type: e.target.value as "FIXED" | "PERCENT" })}
              options={[
                { value: "FIXED", label: "Fixed amount" },
                { value: "PERCENT", label: "Percent of balance" },
              ]}
            />
          </Field>
          <Field label={settings.late_fee_type === "PERCENT" ? "Percent" : "Amount"}>
            <TextInput type="number" step="0.01" min="0" value={settings.late_fee_amount} onChange={(e) => update({ late_fee_amount: e.target.value })} />
          </Field>
          <Field label="Days after due date">
            <TextInput type="number" min="0" value={settings.late_fee_grace_days} onChange={(e) => update({ late_fee_grace_days: Number(e.target.value) })} />
          </Field>
        </div>
      </Card>

      <Card title="Reminders">
        <label className="mb-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={settings.reminders_enabled} onChange={(e) => update({ reminders_enabled: e.target.checked })} />
          Email customers about overdue invoices
        </label>
        <div className="w-60">
          <Field label="Days after the due date">
            <TextInput
              type="number"
              min="0"
              value={settings.reminder_days_after_due}
              onChange={(e) => update({ reminder_days_after_due: Number(e.target.value) })}
            />
          </Field>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          Late fees and reminders run every day through the daily job, or right away from the Invoices page.
        </p>
      </Card>

      <div className="flex justify-end">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}
