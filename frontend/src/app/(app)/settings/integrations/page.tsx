"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { appConfig } from "@/config/app.config";
import { useLoad } from "@/hooks/useLoad";
import { platformService } from "@/services";

/** API keys for other programs, and webhooks that tell them when records change. */
export default function IntegrationsPage() {
  const keys = useLoad(() => platformService.apiKeys());
  const hooks = useLoad(() => platformService.webhooks());
  const deliveries = useLoad(() => platformService.webhookDeliveries());
  const [keyName, setKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState("*");
  const [error, setError] = useState<string | null>(null);
  const signatureHeader = "X-" + appConfig.appName.replace(/[^A-Za-z0-9]/g, "") + "-Signature";
  const docsUrl = appConfig.apiBaseUrl.replace(/\/api\/v\d+$/, "") + "/docs";

  async function createKey(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await platformService.createApiKey(keyName);
      setNewKey(created.key);
      setKeyName("");
      keys.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not create the key.");
    }
  }

  async function revoke(id: number) {
    if (window.confirm("Revoke this key? Programs using it stop working.")) {
      await platformService.revokeApiKey(id);
      keys.reload();
    }
  }

  async function addWebhook(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const list = events
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item);
      await platformService.saveWebhook(url, list);
      setUrl("");
      hooks.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not add the webhook.");
    }
  }

  async function removeWebhook(id: number) {
    if (window.confirm("Delete this webhook?")) {
      await platformService.deleteWebhook(id);
      hooks.reload();
    }
  }

  return (
    <div className="space-y-6">
      <ErrorMessage message={error} />
      <Card title="REST API">
        <p className="text-sm text-gray-600">
          Everything in {appConfig.appName} is available through the REST API. The full reference is at{" "}
          <a href={docsUrl} target="_blank" rel="noreferrer" className="text-brand-700 hover:underline">
            {docsUrl}
          </a>
          . Programs sign in with an API key sent as <code>Authorization: Bearer &lt;key&gt;</code>; they act as you, with your role.
        </p>
      </Card>

      <Card title="API keys">
        {newKey && (
          <div className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
            Copy this key now - it will not be shown again:
            <div className="mt-1 break-all font-mono">{newKey}</div>
          </div>
        )}
        <form onSubmit={createKey} className="mb-4 flex items-end gap-3">
          <div className="w-72">
            <Field label="Key name">
              <TextInput required value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="e.g. Online store" />
            </Field>
          </div>
          <Button type="submit" variant="secondary">
            Create key
          </Button>
        </form>
        <DataTable
          rows={keys.data || []}
          rowKey={(row) => row.id}
          emptyText="No API keys."
          columns={[
            { header: "Name", render: (row) => row.name },
            { header: "Key", render: (row) => <code>{row.prefix}…</code> },
            { header: "Last used", render: (row) => (row.last_used_at ? new Date(row.last_used_at).toLocaleString() : "Never") },
            {
              header: "Status",
              align: "right",
              render: (row) =>
                row.is_active ? (
                  <button onClick={() => revoke(row.id)} className="text-sm text-red-600 hover:underline">
                    Revoke
                  </button>
                ) : (
                  "Revoked"
                ),
            },
          ]}
        />
      </Card>

      <Card title="Webhooks">
        <p className="mb-3 text-sm text-gray-600">
          {appConfig.appName} sends a POST to each URL when records change, e.g. <code>invoice.created</code>, <code>customer.changed</code>,{" "}
          <code>payment.created</code> (* = everything). Each delivery is signed with the webhook&apos;s secret in the {signatureHeader} header.
          With WEBHOOK_DELIVERY=log (the default) deliveries are only recorded below, not sent.
        </p>
        <form onSubmit={addWebhook} className="mb-4 flex flex-wrap items-end gap-3">
          <div className="w-96">
            <Field label="URL">
              <TextInput required type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." />
            </Field>
          </div>
          <div className="w-64">
            <Field label="Events (comma separated)">
              <TextInput required value={events} onChange={(e) => setEvents(e.target.value)} />
            </Field>
          </div>
          <Button type="submit" variant="secondary">
            Add webhook
          </Button>
        </form>
        <DataTable
          rows={hooks.data || []}
          rowKey={(row) => row.id}
          emptyText="No webhooks."
          columns={[
            { header: "URL", render: (row) => row.url },
            { header: "Events", render: (row) => row.events.join(", ") },
            { header: "Secret", render: (row) => <code className="text-xs">{row.secret}</code> },
            {
              header: "Delete",
              align: "right",
              render: (row) => (
                <button onClick={() => removeWebhook(row.id)} className="text-sm text-red-600 hover:underline">
                  Delete
                </button>
              ),
            },
          ]}
        />
      </Card>

      <Card title="Recent deliveries">
        <DataTable
          rows={deliveries.data || []}
          rowKey={(row) => row.id}
          emptyText="Nothing sent yet."
          columns={[
            { header: "When", render: (row) => new Date(row.created_at).toLocaleString() },
            { header: "Event", render: (row) => row.event },
            { header: "Result", render: (row) => row.status + (row.response_code ? " (" + row.response_code + ")" : "") },
            { header: "Error", render: (row) => <span className="text-xs text-red-700">{row.error}</span> },
          ]}
        />
      </Card>
    </div>
  );
}
