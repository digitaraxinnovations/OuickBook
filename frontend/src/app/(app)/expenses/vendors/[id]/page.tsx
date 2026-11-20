"use client";

import { Pencil, Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ContactForm } from "@/components/forms/ContactForm";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { findPurchaseFormByType } from "@/config/purchase-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { expenseService, purchaseService, termsService, vendorService } from "@/services";
import { ContactInput } from "@/types/inputs";

interface ActivityRow {
  key: string;
  date: string;
  type: string;
  number: string;
  status: string;
  overdue: boolean;
  total: string;
  href: string;
}

async function loadActivity(vendorId: number): Promise<ActivityRow[]> {
  const rows: ActivityRow[] = [];
  const documents = await purchaseService.list({ vendor_id: vendorId });
  for (const document of documents) {
    const form = findPurchaseFormByType(document.doc_type);
    rows.push({
      key: "doc-" + document.id,
      date: document.doc_date,
      type: form.title,
      number: document.doc_number || "-",
      status: document.status,
      overdue: document.is_overdue,
      total: document.total,
      href: "/expenses/forms/" + form.slug + "/" + document.id,
    });
  }
  // Expenses are listed for all vendors; keep this vendor's.
  const expenses = await expenseService.list();
  for (const expense of expenses) {
    if (expense.vendor?.id !== vendorId) {
      continue;
    }
    rows.push({
      key: "expense-" + expense.id,
      date: expense.expense_date,
      type: expense.kind === "CHECK" ? "Check" : "Expense",
      number: expense.check_number || "-",
      status: expense.is_void ? "VOID" : "PAID",
      overdue: false,
      total: expense.total,
      href: "/expenses/" + expense.id,
    });
  }
  rows.sort((a, b) => (a.date < b.date ? 1 : -1));
  return rows;
}

export default function VendorDetailPage() {
  const params = useParams<{ id: string }>();
  const vendorId = Number(params.id);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;
  const vendor = useLoad(() => vendorService.get(vendorId), [vendorId]);
  const activity = useLoad(() => loadActivity(vendorId), [vendorId]);
  const terms = useLoad(() => termsService.list());
  const [editOpen, setEditOpen] = useState(false);

  if (vendor.loading) {
    return <Loading />;
  }
  if (!vendor.data) {
    return <ErrorMessage message={vendor.error} />;
  }
  const data = vendor.data;

  async function saveVendor(input: ContactInput) {
    await vendorService.update(data.id, input);
    setEditOpen(false);
    vendor.reload();
  }

  return (
    <div>
      <PageHeader
        title={data.display_name}
        subtitle={[data.company_name, data.email, data.phone].filter(Boolean).join(" · ")}
        actions={
          <>
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              <Pencil size={16} /> Edit
            </Button>
            <LinkButton href={"/expenses/pay-bills?vendor=" + data.id} variant="secondary">
              Pay bills
            </LinkButton>
            <LinkButton href="/expenses/forms/bills/new">
              <Plus size={16} /> New bill
            </LinkButton>
          </>
        }
      />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Open balance</div>
          <div className="mt-1 text-2xl font-semibold">{formatMoney(data.open_balance, currency)}</div>
        </Card>
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">1099 contractor</div>
          <div className="mt-1 text-sm">{data.track_1099 ? "Yes" + (data.tax_id ? " · Tax ID " + data.tax_id : "") : "No"}</div>
        </Card>
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Address</div>
          <div className="mt-1 whitespace-pre-line text-sm">{data.address || "-"}</div>
        </Card>
      </div>

      <h2 className="mb-3 text-lg font-semibold">Transactions</h2>
      {activity.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={activity.data || []}
          rowKey={(row) => row.key}
          onRowClick={(row) => router.push(row.href)}
          emptyText="No transactions with this vendor yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.date) },
            { header: "Type", render: (row) => row.type },
            { header: "No.", render: (row) => row.number },
            { header: "Status", render: (row) => <StatusBadge status={row.status} overdue={row.overdue} /> },
            { header: "Total", align: "right", render: (row) => formatMoney(row.total, currency) },
          ]}
        />
      )}

      <Modal title="Edit vendor" open={editOpen} onClose={() => setEditOpen(false)}>
        <ContactForm key={data.id + "-" + editOpen} initial={data} terms={terms.data || []} vendorFields onSave={saveVendor} onCancel={() => setEditOpen(false)} />
      </Modal>
    </div>
  );
}
