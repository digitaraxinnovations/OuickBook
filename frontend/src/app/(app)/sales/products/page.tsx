"use client";

import { Download, Plus, Upload } from "lucide-react";
import { MouseEvent, useEffect, useState } from "react";
import { ProductForm } from "@/components/forms/ProductForm";
import { ProductImportDialog } from "@/components/inventory/ProductImportDialog";
import { StockHistoryDialog } from "@/components/inventory/StockHistoryDialog";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { saveBlob } from "@/lib/files";
import { formatLabel, formatMoney, toNumber } from "@/lib/format";
import { accountService, inventoryService, productService } from "@/services";
import { ProductInput } from "@/types/inputs";
import { Product } from "@/types/models";

const FILTERS = [
  { value: "LOW_STOCK", label: "Low stock" },
  { value: "INVENTORY", label: "Inventory items" },
  { value: "NON_INVENTORY", label: "Non-inventory" },
  { value: "SERVICE", label: "Services" },
  { value: "BUNDLE", label: "Bundles" },
];

function matchesFilter(product: Product, filter: string): boolean {
  if (!filter) {
    return true;
  }
  if (filter === "LOW_STOCK") {
    return product.is_low_stock;
  }
  return product.product_type === filter;
}

export default function ProductsPage() {
  const { company } = useAuth();
  const products = useLoad(() => productService.list());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const categories = useLoad(() => inventoryService.categories());
  const [editing, setEditing] = useState<Product | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [historyFor, setHistoryFor] = useState<Product | null>(null);
  const [filter, setFilter] = useState("");
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setFormOpen(true);
    }
  }, [openFromMenu]);

  if (accounts.loading || categories.loading) {
    return <Loading />;
  }

  const allProducts = products.data || [];
  const lowStockCount = allProducts.filter((product) => product.is_low_stock).length;
  const rows = allProducts.filter((product) => matchesFilter(product, filter));

  async function save(input: ProductInput) {
    if (editing) {
      await productService.update(editing.id, input);
    } else {
      await productService.create(input);
    }
    setFormOpen(false);
    products.reload();
  }

  async function exportCsv() {
    saveBlob(await inventoryService.exportProducts(), "products-and-services.csv");
  }

  function openNew() {
    setEditing(null);
    setFormOpen(true);
  }

  function showHistory(event: MouseEvent, product: Product) {
    event.stopPropagation();
    setHistoryFor(product);
  }

  return (
    <div>
      <PageHeader
        title="Products and services"
        subtitle="Things you sell and buy. Inventory items keep count of what is on hand."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              <Upload size={16} /> Import
            </Button>
            <Button variant="secondary" onClick={exportCsv}>
              <Download size={16} /> Export
            </Button>
            <Button onClick={openNew}>
              <Plus size={16} /> New item
            </Button>
          </div>
        }
      />
      <ErrorMessage message={products.error} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select className="w-48!" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="All items" options={FILTERS} />
        {lowStockCount > 0 && (
          <button onClick={() => setFilter("LOW_STOCK")} className="rounded-full bg-amber-50 px-3 py-1 text-sm text-amber-800">
            {lowStockCount} item(s) low on stock
          </button>
        )}
      </div>
      {products.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={rows}
          rowKey={(row) => row.id}
          onRowClick={(row) => {
            setEditing(row);
            setFormOpen(true);
          }}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "SKU", render: (row) => row.sku },
            { header: "Type", render: (row) => formatLabel(row.product_type) },
            { header: "Category", render: (row) => (row.category ? row.category.name : "") },
            {
              header: "Qty on hand",
              align: "right",
              render: (row) =>
                row.product_type === "INVENTORY" ? (
                  <span className="whitespace-nowrap">
                    {row.is_low_stock && <span className="mr-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800">Low</span>}
                    {toNumber(row.quantity_on_hand)}
                  </span>
                ) : (
                  ""
                ),
            },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
            { header: "Price", align: "right", render: (row) => formatMoney(row.sales_price, company?.currency) },
            {
              header: "History",
              align: "right",
              render: (row) =>
                row.product_type === "INVENTORY" ? (
                  <button onClick={(event) => showHistory(event, row)} className="text-sm text-brand-700 hover:underline">
                    History
                  </button>
                ) : null,
            },
          ]}
        />
      )}
      <Modal title={editing ? "Edit item" : "New item"} open={formOpen} onClose={() => setFormOpen(false)} wide>
        <ProductForm
          key={editing ? editing.id : "new"}
          initial={editing}
          accounts={accounts.data || []}
          categories={categories.data || []}
          products={allProducts}
          currency={company?.currency}
          onSave={save}
          onCancel={() => setFormOpen(false)}
        />
      </Modal>
      {importOpen && <ProductImportDialog open={importOpen} onClose={() => setImportOpen(false)} onImported={products.reload} />}
      {historyFor && <StockHistoryDialog product={historyFor} currency={company?.currency} onClose={() => setHistoryFor(null)} />}
    </div>
  );
}
