"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { ProductForm } from "@/components/forms/ProductForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatLabel, formatMoney } from "@/lib/format";
import { accountService, productService } from "@/services";
import { ProductInput } from "@/types/inputs";
import { Product } from "@/types/models";

export default function ProductsPage() {
  const { company } = useAuth();
  const products = useLoad(() => productService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [editing, setEditing] = useState<Product | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setFormOpen(true);
    }
  }, [openFromMenu]);

  const incomeAccounts = (accounts.data || []).filter((account) => account.account_type === "INCOME");

  async function save(input: ProductInput) {
    if (editing) {
      await productService.update(editing.id, input);
    } else {
      await productService.create(input);
    }
    setFormOpen(false);
    products.reload();
  }

  return (
    <div>
      <PageHeader
        title="Products and services"
        subtitle="Things you sell. Pick them on invoices to fill in the description and price."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} /> New item
          </Button>
        }
      />
      <ErrorMessage message={products.error} />
      {products.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={products.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => {
            setEditing(row);
            setFormOpen(true);
          }}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "SKU", render: (row) => row.sku },
            { header: "Type", render: (row) => formatLabel(row.product_type) },
            { header: "Income account", render: (row) => row.income_account.name },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
            { header: "Price", align: "right", render: (row) => formatMoney(row.sales_price, company?.currency) },
          ]}
        />
      )}
      <Modal title={editing ? "Edit item" : "New item"} open={formOpen} onClose={() => setFormOpen(false)}>
        <ProductForm
          key={editing ? editing.id : "new"}
          initial={editing}
          incomeAccounts={incomeAccounts}
          onSave={save}
          onCancel={() => setFormOpen(false)}
        />
      </Modal>
    </div>
  );
}
