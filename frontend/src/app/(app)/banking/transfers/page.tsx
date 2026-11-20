"use client";

import { Plus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate, formatMoney, todayString } from "@/lib/format";
import { accountService, bankingService } from "@/services";
import { Transfer } from "@/types/models";

export default function TransfersPage() {
  const { company } = useAuth();
  const transfers = useLoad(() => bankingService.transfers());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [open, setOpen] = useState(false);
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [amount, setAmount] = useState("");
  const [transferDate, setTransferDate] = useState(todayString());
  const [memo, setMemo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setOpen(true);
    }
  }, [openFromMenu]);

  // Transfers are between bank, card and other balance-sheet accounts.
  const accountOptions = (accounts.data || [])
    .filter(
      (account) =>
        (account.account_type === "ASSET" || account.account_type === "LIABILITY") &&
        account.system_key !== "accounts_receivable" &&
        account.system_key !== "accounts_payable",
    )
    .map((account) => ({ value: account.id, label: account.full_name }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await bankingService.createTransfer({
        transfer_date: transferDate,
        from_account_id: Number(fromId),
        to_account_id: Number(toId),
        amount: amount,
        memo: memo,
      });
      setOpen(false);
      setAmount("");
      setMemo("");
      transfers.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  async function voidTransfer(transfer: Transfer) {
    if (window.confirm("Void this transfer?")) {
      await bankingService.voidTransfer(transfer.id);
      transfers.reload();
    }
  }

  return (
    <div>
      <PageHeader
        title="Transfers"
        subtitle="Money moved between your own accounts - including paying off a credit card."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New transfer
          </Button>
        }
      />
      <ErrorMessage message={transfers.error} />
      {transfers.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={transfers.data || []}
          rowKey={(row) => row.id}
          emptyText="No transfers yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.transfer_date) },
            { header: "From", render: (row) => row.from_account.name },
            { header: "To", render: (row) => row.to_account.name },
            { header: "Memo", render: (row) => row.memo },
            {
              header: "Amount",
              align: "right",
              render: (row) => (row.is_void ? <span className="text-gray-400">Void</span> : formatMoney(row.amount, company?.currency)),
            },
            {
              header: "",
              align: "right",
              render: (row) =>
                row.is_void ? null : (
                  <button onClick={() => voidTransfer(row)} className="text-sm text-gray-500 hover:text-red-600">
                    Void
                  </button>
                ),
            },
          ]}
        />
      )}
      <Modal title="New transfer" open={open} onClose={() => setOpen(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <ErrorMessage message={error} />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Transfer from" required>
              <Select required value={fromId} onChange={(e) => setFromId(e.target.value)} placeholder="Choose" options={accountOptions} />
            </Field>
            <Field label="Transfer to" required>
              <Select required value={toId} onChange={(e) => setToId(e.target.value)} placeholder="Choose" options={accountOptions} />
            </Field>
            <Field label="Amount" required>
              <TextInput type="number" step="0.01" min="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
            </Field>
            <Field label="Date" required>
              <TextInput type="date" required value={transferDate} onChange={(e) => setTransferDate(e.target.value)} />
            </Field>
          </div>
          <Field label="Memo">
            <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
          </Field>
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
