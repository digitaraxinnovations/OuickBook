"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { inventoryService } from "@/services";
import { ProductImportResult } from "@/types/models";

interface ProductImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

/** Upload a CSV of products and services (same columns as the export). */
export function ProductImportDialog({ open, onClose, onImported }: ProductImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ProductImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const outcome = await inventoryService.importProducts(await file.text());
      setResult(outcome);
      if (outcome.errors.length === 0) {
        onImported();
      }
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not import the file.");
    }
    setSaving(false);
  }

  return (
    <Modal title="Import products and services" open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <p className="text-sm text-gray-600">
          Use a CSV file with a header row. Columns: Name, SKU, Type (Service, Non-inventory or Inventory), Description, Sales price,
          Purchase cost, Taxable, Category, Quantity on hand, Reorder point, Active. Only Name is required. Items with a name that already
          exists are updated. Tip: export first to get a file in the right format.
        </p>
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)} className="text-sm" />
        {result && result.errors.length === 0 && (
          <div className="rounded-md bg-green-50 p-3 text-sm text-green-800">
            Added {result.created} and updated {result.updated} items.
          </div>
        )}
        {result && result.errors.length > 0 && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
            <div className="mb-1 font-medium">Nothing was imported. Fix these rows and try again:</div>
            <ul className="list-disc pl-5">
              {result.errors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button type="submit" disabled={!file || saving}>
            {saving ? "Importing..." : "Import"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
