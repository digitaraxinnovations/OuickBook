"use client";

import { useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { useLoad } from "@/hooks/useLoad";
import { companySettingsService } from "@/services";
import { EmailLogEntry } from "@/types/models";

const statusText: Record<string, string> = {
  LOGGED: "Recorded only",
  SENT: "Sent",
  FAILED: "Failed",
};

export default function EmailLogPage() {
  const log = useLoad(() => companySettingsService.emailLog());
  const [open, setOpen] = useState<EmailLogEntry | null>(null);

  return (
    <div>
      <p className="mb-4 text-sm text-gray-600">
        Every email sent from the app. &quot;Recorded only&quot; means no email server is set up yet (EMAIL_PROVIDER=log), so the message
        was saved here instead of being sent.
      </p>
      <ErrorMessage message={log.error} />
      {log.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={log.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => setOpen(row)}
          emptyText="No emails yet."
          columns={[
            { header: "When", render: (row) => new Date(row.sent_at).toLocaleString() },
            { header: "To", render: (row) => row.to_address },
            { header: "Subject", render: (row) => row.subject },
            { header: "Attachment", render: (row) => row.attachment_name },
            {
              header: "Status",
              render: (row) => <span className={row.status === "FAILED" ? "text-red-600" : ""}>{statusText[row.status] || row.status}</span>,
            },
          ]}
        />
      )}
      <Modal title={open?.subject || ""} open={open !== null} onClose={() => setOpen(null)} wide>
        {open && (
          <div className="space-y-2 text-sm">
            <div>
              <strong>To:</strong> {open.to_address}
            </div>
            {open.attachment_name && (
              <div>
                <strong>Attachment:</strong> {open.attachment_name}
              </div>
            )}
            {open.error && <div className="text-red-600">{open.error}</div>}
            <pre className="mt-3 whitespace-pre-wrap rounded bg-gray-50 p-4 font-sans">{open.body}</pre>
          </div>
        )}
      </Modal>
    </div>
  );
}
