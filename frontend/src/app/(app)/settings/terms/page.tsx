"use client";

import { Plus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { useLoad } from "@/hooks/useLoad";
import { termsService } from "@/services";
import { PaymentTerm } from "@/types/models";

export default function PaymentTermsPage() {
  const terms = useLoad(() => termsService.list());
  const [editing, setEditing] = useState<PaymentTerm | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [dueDays, setDueDays] = useState("30");
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function openForm(term: PaymentTerm | null) {
    setEditing(term);
    setName(term ? term.name : "");
    setDueDays(term ? String(term.due_days) : "30");
    setIsActive(term ? term.is_active : true);
    setError(null);
    setOpen(true);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const input = { name: name, due_days: Number(dueDays), is_active: isActive };
    try {
      if (editing) {
        await termsService.update(editing.id, input);
      } else {
        await termsService.create(input);
      }
      setOpen(false);
      terms.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-600">Terms set an invoice&apos;s due date. Customers can have their own default terms.</p>
        <Button onClick={() => openForm(null)}>
          <Plus size={16} /> New terms
        </Button>
      </div>
      <ErrorMessage message={terms.error} />
      {terms.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={terms.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => openForm(row)}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "Due in", render: (row) => (row.due_days === 0 ? "Immediately" : row.due_days + " days") },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
          ]}
        />
      )}
      <Modal title={editing ? "Edit terms" : "New terms"} open={open} onClose={() => setOpen(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <ErrorMessage message={error} />
          <Field label="Name" required>
            <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Net 45" />
          </Field>
          <Field label="Due in days" required>
            <TextInput type="number" min="0" max="365" required value={dueDays} onChange={(e) => setDueDays(e.target.value)} />
          </Field>
          {editing && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Active
            </label>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Save</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
