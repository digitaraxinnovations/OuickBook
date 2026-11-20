"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { AccountForm } from "@/components/forms/AccountForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatLabel, formatMoney } from "@/lib/format";
import { accountService, taxService } from "@/services";
import { AccountInput } from "@/types/inputs";
import { Account } from "@/types/models";

export default function ChartOfAccountsPage() {
  const { company } = useAuth();
  const accounts = useLoad(() => accountService.list());
  const boxes = useLoad(() => accountService.boxes1099());
  const taxLines = useLoad(() => taxService.taxLines());
  const [editing, setEditing] = useState<Account | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  async function save(input: AccountInput) {
    if (editing) {
      await accountService.update(editing.id, input);
    } else {
      await accountService.create(input);
    }
    setFormOpen(false);
    accounts.reload();
  }

  return (
    <div>
      <PageHeader
        title="Chart of accounts"
        subtitle="Every account your money moves through. Balances update automatically."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} /> New account
          </Button>
        }
      />
      <ErrorMessage message={accounts.error} />
      {accounts.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={accounts.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => {
            setEditing(row);
            setFormOpen(true);
          }}
          columns={[
            { header: "Number", render: (row) => row.code },
            {
              header: "Name",
              render: (row) => (
                <span
                  style={{ paddingLeft: row.depth * 20 }}
                  className={(row.is_active ? "" : "text-gray-400 ") + (row.depth === 0 ? "font-medium" : "")}
                >
                  {row.depth > 0 && <span className="mr-1 text-gray-400">└</span>}
                  {row.name}
                  {!row.is_active && " (inactive)"}
                </span>
              ),
            },
            { header: "Type", render: (row) => formatLabel(row.account_type) },
            { header: "Detail type", render: (row) => row.detail_type },
            { header: "Balance", align: "right", render: (row) => formatMoney(row.balance, company?.currency) },
          ]}
        />
      )}
      <Modal title={editing ? "Edit account" : "New account"} open={formOpen} onClose={() => setFormOpen(false)}>
        <AccountForm
          key={editing ? editing.id : "new"}
          initial={editing}
          allAccounts={accounts.data || []}
          boxes1099={boxes.data || {}}
          taxLines={taxLines.data || {}}
          onSave={save}
          onCancel={() => setFormOpen(false)}
        />
      </Modal>
    </div>
  );
}
