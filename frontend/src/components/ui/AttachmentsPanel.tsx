"use client";

import { Paperclip, Trash2 } from "lucide-react";
import { ChangeEvent, useState } from "react";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/Feedback";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab, readFileAsBase64 } from "@/lib/files";
import { attachmentService } from "@/services";

interface AttachmentsPanelProps {
  entityType: string;
  entityId: number;
}

/** Shows the files attached to one transaction and lets the user add or remove them. */
export function AttachmentsPanel({ entityType, entityId }: AttachmentsPanelProps) {
  const files = useLoad(() => attachmentService.list(entityType, entityId), [entityType, entityId]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await attachmentService.upload(entityType, entityId, file, await readFileAsBase64(file));
      files.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not upload the file.");
    } finally {
      setUploading(false);
    }
  }

  async function open(id: number) {
    try {
      openBlobInNewTab(await attachmentService.download(id));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not open the file.");
    }
  }

  async function remove(id: number) {
    if (!window.confirm("Remove this attachment?")) {
      return;
    }
    await attachmentService.remove(id);
    files.reload();
  }

  return (
    <Card title="Attachments" className="no-print mt-6">
      <ErrorMessage message={error} />
      {(files.data || []).length === 0 && <p className="mb-3 text-sm text-gray-500">No files attached.</p>}
      <ul className="mb-3 divide-y divide-gray-100">
        {(files.data || []).map((file) => (
          <li key={file.id} className="flex items-center justify-between py-2 text-sm">
            <button type="button" onClick={() => open(file.id)} className="flex items-center gap-2 text-brand-700 hover:underline">
              <Paperclip size={14} /> {file.filename}
            </button>
            <span className="flex items-center gap-3 text-gray-500">
              {Math.ceil(file.size_bytes / 1024)} KB
              <button type="button" onClick={() => remove(file.id)} className="hover:text-red-600" aria-label="Remove attachment">
                <Trash2 size={14} />
              </button>
            </span>
          </li>
        ))}
      </ul>
      <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-brand-700">
        <Paperclip size={16} /> {uploading ? "Uploading..." : "Attach a file"}
        <input type="file" className="hidden" accept="image/*,application/pdf,text/plain,text/csv" onChange={upload} disabled={uploading} />
      </label>
    </Card>
  );
}
