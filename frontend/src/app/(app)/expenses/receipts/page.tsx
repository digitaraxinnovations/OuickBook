"use client";

import { FileText, Trash2, Upload } from "lucide-react";
import { ChangeEvent, useState } from "react";
import { LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading, SuccessMessage } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab, readFileAsBase64 } from "@/lib/files";
import { attachmentService } from "@/services";

/**
 * Receipts inbox: upload receipt photos or PDFs now, then turn each one into an
 * expense (the receipt is attached to it). Reading amounts off the image
 * automatically (OCR) needs an outside service and is not included.
 */
export default function ReceiptsPage() {
  const receipts = useLoad(() => attachmentService.receipts());
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files ? Array.from(event.target.files) : [];
    event.target.value = "";
    setError(null);
    setMessage(null);
    setUploading(true);
    try {
      for (const file of files) {
        await attachmentService.upload("RECEIPT", null, file, await readFileAsBase64(file));
      }
      setMessage(files.length + " receipt(s) uploaded.");
      receipts.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not upload.");
    } finally {
      setUploading(false);
    }
  }

  async function view(id: number) {
    try {
      openBlobInNewTab(await attachmentService.download(id));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not open the file.");
    }
  }

  async function remove(id: number) {
    if (!window.confirm("Delete this receipt?")) {
      return;
    }
    await attachmentService.remove(id);
    receipts.reload();
  }

  return (
    <div>
      <PageHeader title="Receipts" subtitle="Upload receipts, then create an expense from each one." />
      <ErrorMessage message={error || receipts.error} />
      <SuccessMessage message={message} />

      <Card className="mb-6">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-gray-300 py-8 text-sm text-gray-600 hover:border-brand-500">
          <Upload size={24} className="text-brand-600" />
          {uploading ? "Uploading..." : "Click to choose receipt images or PDFs (you can pick several)"}
          <input type="file" multiple accept="image/*,application/pdf" className="hidden" onChange={upload} disabled={uploading} />
        </label>
      </Card>

      {receipts.loading ? (
        <Loading />
      ) : (receipts.data || []).length === 0 ? (
        <p className="text-sm text-gray-500">No receipts waiting. Receipts move off this list once added to an expense.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(receipts.data || []).map((receipt) => (
            <Card key={receipt.id}>
              <button type="button" onClick={() => view(receipt.id)} className="flex items-center gap-2 text-left text-sm font-medium text-brand-700 hover:underline">
                <FileText size={18} /> {receipt.filename}
              </button>
              <div className="mt-1 text-xs text-gray-500">
                Uploaded {new Date(receipt.created_at).toLocaleDateString()} · {Math.ceil(receipt.size_bytes / 1024)} KB
              </div>
              <div className="mt-4 flex items-center justify-between">
                <LinkButton href={"/expenses/new?receipt=" + receipt.id}>Create expense</LinkButton>
                <button type="button" onClick={() => remove(receipt.id)} className="text-gray-400 hover:text-red-600" aria-label="Delete receipt">
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
