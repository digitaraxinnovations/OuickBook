"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { bankingService } from "@/services";
import { StatementImportResult } from "@/types/models";

interface ImportStatementDialogProps {
  open: boolean;
  accountId: number;
  accountName: string;
  onClose: () => void;
  onImported: (result: StatementImportResult) => void;
}

/** Upload a CSV, OFX or QFX statement. CSV columns are found automatically unless named here. */
export function ImportStatementDialog({ open, accountId, accountName, onClose, onImported }: ImportStatementDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [showCsvOptions, setShowCsvOptions] = useState(false);
  const [dateColumn, setDateColumn] = useState("");
  const [descriptionColumn, setDescriptionColumn] = useState("");
  const [amountColumn, setAmountColumn] = useState("");
  const [dateFormat, setDateFormat] = useState("");
  const [reverseSigns, setReverseSigns] = useState(false);
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
      const result = await bankingService.importStatement({
        account_id: accountId,
        filename: file.name,
        content: await file.text(),
        date_column: dateColumn,
        description_column: descriptionColumn,
        amount_column: amountColumn,
        debit_column: "",
        credit_column: "",
        date_format: dateFormat,
        reverse_signs: reverseSigns,
      });
      onImported(result);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not import the file.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={"Upload statement - " + accountName} open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <p className="text-sm text-gray-600">
          Download a statement from your bank&apos;s website as CSV, OFX, QFX or QBO, and choose it here. Lines you already imported are skipped.
        </p>
        <input type="file" required accept=".csv,.txt,.ofx,.qfx,.qbo" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-sm" />
        <button type="button" className="block text-sm text-brand-700 hover:underline" onClick={() => setShowCsvOptions(!showCsvOptions)}>
          {showCsvOptions ? "Hide" : "Show"} CSV options
        </button>
        {showCsvOptions && (
          <div className="space-y-3 rounded-md bg-gray-50 p-4">
            <p className="text-xs text-gray-500">Leave empty to detect from the header row. Type the column names exactly as in the file.</p>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Date column">
                <TextInput value={dateColumn} onChange={(e) => setDateColumn(e.target.value)} />
              </Field>
              <Field label="Description column">
                <TextInput value={descriptionColumn} onChange={(e) => setDescriptionColumn(e.target.value)} />
              </Field>
              <Field label="Amount column">
                <TextInput value={amountColumn} onChange={(e) => setAmountColumn(e.target.value)} />
              </Field>
            </div>
            <Field label="Date format (e.g. %d/%m/%Y)">
              <TextInput value={dateFormat} onChange={(e) => setDateFormat(e.target.value)} />
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={reverseSigns} onChange={(e) => setReverseSigns(e.target.checked)} />
              Money out is shown as positive numbers in this file
            </label>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !file}>
            {saving ? "Importing..." : "Import"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
