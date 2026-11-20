"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { AttachmentsPanel } from "@/components/ui/AttachmentsPanel";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { findPurchaseFormBySlug } from "@/config/purchase-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, todayString, toNumber } from "@/lib/format";
import { purchaseService } from "@/services";

export default function PurchaseFormDetailPage() {
  const params = useParams<{ slug: string; id: string }>();
  const form = findPurchaseFormBySlug(params.slug);
  const documentId = Number(params.id);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;
  const document = useLoad(() => purchaseService.get(documentId), [documentId]);
  const payments = useLoad(() => purchaseService.payments(documentId), [documentId]);
  const [convertOpen, setConvertOpen] = useState(false);
  const [billDate, setBillDate] = useState(todayString());
  const [billNumber, setBillNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!form) {
    return <ErrorMessage message="This page does not exist." />;
  }
  if (document.loading) {
    return <Loading />;
  }
  if (!document.data) {
    return <ErrorMessage message={document.error} />;
  }
  const data = document.data;
  const config = form;
  const isBill = data.doc_type === "BILL";
  const isOrder = data.doc_type === "PURCHASE_ORDER";

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
  }

  function voidDocument() {
    if (!window.confirm("Void this " + config.title.toLowerCase() + "?")) {
      return;
    }
    run(async () => {
      await purchaseService.void(data.id);
      document.reload();
    });
  }

  function closeOrder() {
    run(async () => {
      await purchaseService.close(data.id);
      document.reload();
    });
  }

  function convert() {
    run(async () => {
      const bill = await purchaseService.convertToBill(data.id, billDate, billNumber);
      router.push("/expenses/forms/bills/" + bill.id);
    });
  }

  return (
    <div>
      <PageHeader
        title={config.title + (data.doc_number ? " " + data.doc_number : "")}
        actions={
          <>
            {isOrder && data.status === "OPEN" && (
              <>
                <Button variant="secondary" onClick={closeOrder}>
                  Close order
                </Button>
                <Button onClick={() => setConvertOpen(true)}>Create bill</Button>
              </>
            )}
            {data.status !== "VOID" && toNumber(data.amount_applied) === 0 && (
              <Button variant="danger" onClick={voidDocument}>
                Void
              </Button>
            )}
            {isBill && toNumber(data.balance) > 0 && (
              <LinkButton href={"/expenses/pay-bills?vendor=" + data.vendor.id}>Pay bill</LinkButton>
            )}
          </>
        }
      />
      <ErrorMessage message={error} />

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="grid gap-6 text-sm sm:grid-cols-4">
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Vendor</div>
              <Link href={"/expenses/vendors/" + data.vendor.id} className="mt-1 block font-medium text-brand-700 hover:underline">
                {data.vendor.display_name}
              </Link>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Date</div>
              <div className="mt-1">{formatDate(data.doc_date)}</div>
            </div>
            {data.due_date && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">Due date</div>
                <div className={"mt-1 " + (data.is_overdue ? "text-red-600" : "")}>{formatDate(data.due_date)}</div>
              </div>
            )}
            {data.purchase_order_id && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">From order</div>
                <Link href={"/expenses/forms/purchase-orders/" + data.purchase_order_id} className="mt-1 block text-brand-700 hover:underline">
                  View purchase order
                </Link>
              </div>
            )}
          </div>
          <StatusBadge status={data.status} overdue={data.is_overdue} />
        </div>

        <table className="mt-6 w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Category</th>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Qty</th>
              <th className="py-2 text-right">Rate</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id} className="border-b border-gray-100">
                <td className="py-2">{line.account.name}</td>
                <td className="py-2">{line.description}</td>
                <td className="py-2 text-right">{toNumber(line.quantity)}</td>
                <td className="py-2 text-right">{formatMoney(line.rate, currency)}</td>
                <td className="py-2 text-right">{formatMoney(line.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 flex justify-between gap-6">
          <div className="text-sm text-gray-600">{data.memo}</div>
          <div className="w-64 space-y-1 text-sm">
            <div className="flex justify-between font-semibold">
              <span>Total</span>
              <span>{formatMoney(data.total, currency)}</span>
            </div>
            {!isOrder && (
              <div className="flex justify-between">
                <span>{isBill ? "Balance due" : "Credit left"}</span>
                <span>{formatMoney(data.balance, currency)}</span>
              </div>
            )}
          </div>
        </div>
      </Card>

      {isBill && (
        <div className="mt-6">
          <h2 className="mb-3 text-lg font-semibold">Payments</h2>
          <DataTable
            rows={payments.data || []}
            rowKey={(row) => row.payment_id}
            emptyText="No payments yet."
            columns={[
              { header: "Date", render: (row) => formatDate(row.payment_date) },
              { header: "Method", render: (row) => formatLabel(row.payment_method) + (row.check_number ? " #" + row.check_number : "") },
              { header: "Paid from", render: (row) => row.payment_account.name },
              { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
            ]}
          />
        </div>
      )}

      <AttachmentsPanel entityType={config.attachmentType} entityId={data.id} />

      <Modal title="Create bill from purchase order" open={convertOpen} onClose={() => setConvertOpen(false)}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Bill date">
              <TextInput type="date" value={billDate} onChange={(e) => setBillDate(e.target.value)} />
            </Field>
            <Field label="Vendor's bill no.">
              <TextInput value={billNumber} onChange={(e) => setBillNumber(e.target.value)} />
            </Field>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConvertOpen(false)}>
              Cancel
            </Button>
            <Button onClick={convert}>Create bill</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
