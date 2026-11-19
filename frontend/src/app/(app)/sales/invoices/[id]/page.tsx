"use client";

import { Printer } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ReceivePaymentForm } from "@/components/forms/ReceivePaymentForm";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { accountService, invoiceService } from "@/services";
import { PaymentInput } from "@/types/inputs";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;

  const invoice = useLoad(() => invoiceService.get(invoiceId), [invoiceId]);
  const payments = useLoad(() => invoiceService.listPayments(invoiceId), [invoiceId]);
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (invoice.loading) {
    return <Loading />;
  }
  if (!invoice.data) {
    return <ErrorMessage message={invoice.error} />;
  }
  const data = invoice.data;
  const canTakePayment = data.status === "OPEN" || data.status === "PARTIALLY_PAID";

  // Money can be deposited into any asset account except Accounts Receivable.
  const depositAccounts = (accounts.data || []).filter(
    (account) => account.account_type === "ASSET" && account.system_key !== "accounts_receivable",
  );

  async function savePayment(input: PaymentInput) {
    await invoiceService.receivePayment(input);
    setPaymentOpen(false);
    invoice.reload();
    payments.reload();
  }

  async function voidInvoice() {
    if (!window.confirm("Void invoice " + data.invoice_number + "? This reverses it in your books.")) {
      return;
    }
    setActionError(null);
    try {
      await invoiceService.void(data.id);
      invoice.reload();
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : "Could not void the invoice.");
    }
  }

  return (
    <div>
      <PageHeader
        title={"Invoice " + data.invoice_number}
        actions={
          <>
            <Button variant="secondary" onClick={() => window.print()}>
              <Printer size={16} /> Print
            </Button>
            {data.status === "OPEN" && (
              <Button variant="danger" onClick={voidInvoice}>
                Void
              </Button>
            )}
            {canTakePayment && <Button onClick={() => setPaymentOpen(true)}>Receive payment</Button>}
          </>
        }
      />
      <ErrorMessage message={actionError} />

      <Card>
        <div className="flex flex-wrap justify-between gap-6">
          <div>
            <div className="text-lg font-semibold">{company?.name}</div>
            {company?.address && <div className="whitespace-pre-line text-sm text-gray-600">{company.address}</div>}
            {company?.email && <div className="text-sm text-gray-600">{company.email}</div>}
          </div>
          <div className="text-right">
            <div className="text-2xl font-light uppercase tracking-widest text-gray-400">Invoice</div>
            <div className="mt-2">
              <StatusBadge status={data.status} overdue={data.is_overdue} />
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-6 text-sm md:grid-cols-3">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Bill to</div>
            <div className="mt-1 font-medium">{data.customer.display_name}</div>
            {data.customer.email && <div className="text-gray-600">{data.customer.email}</div>}
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Invoice date</div>
            <div className="mt-1">{formatDate(data.invoice_date)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Due date</div>
            <div className="mt-1">{formatDate(data.due_date)}</div>
          </div>
        </div>

        <table className="mt-8 w-full text-sm">
          <thead className="border-b-2 border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Qty</th>
              <th className="py-2 text-right">Rate</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id} className="border-b border-gray-100">
                <td className="py-3">{line.description}</td>
                <td className="py-3 text-right">{toNumber(line.quantity)}</td>
                <td className="py-3 text-right">{formatMoney(line.rate, currency)}</td>
                <td className="py-3 text-right">{formatMoney(line.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-6 flex justify-between gap-6">
          <div className="max-w-md whitespace-pre-line text-sm text-gray-600">{data.memo}</div>
          <div className="w-64 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Total</span>
              <span className="font-medium">{formatMoney(data.total, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span>Amount paid</span>
              <span>{formatMoney(data.amount_paid, currency)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-200 pt-2 text-base font-semibold">
              <span>Balance due</span>
              <span>{formatMoney(data.balance_due, currency)}</span>
            </div>
          </div>
        </div>
      </Card>

      <div className="no-print mt-8">
        <h2 className="mb-3 text-lg font-semibold">Payments</h2>
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.id}
          emptyText="No payments yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Method", render: (row) => formatLabel(row.payment_method) },
            { header: "Reference", render: (row) => row.reference_no },
            { header: "Deposited to", render: (row) => row.deposit_account.name },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
          ]}
        />
      </div>

      <Modal title={"Receive payment - invoice " + data.invoice_number} open={paymentOpen} onClose={() => setPaymentOpen(false)}>
        <ReceivePaymentForm invoice={data} depositAccounts={depositAccounts} onSave={savePayment} onCancel={() => setPaymentOpen(false)} />
      </Modal>
    </div>
  );
}
