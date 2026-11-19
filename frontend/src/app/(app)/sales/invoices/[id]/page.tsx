"use client";

import { FileDown, Link2, Mail } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { EmailDialog } from "@/components/sales/EmailDialog";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge, SuccessMessage } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { invoiceService } from "@/services";
import { EmailInput } from "@/types/inputs";

function TotalRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={"flex justify-between " + (bold ? "border-t border-gray-200 pt-2 text-base font-semibold" : "")}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;

  const invoice = useLoad(() => invoiceService.get(invoiceId), [invoiceId]);
  const payments = useLoad(() => invoiceService.listPayments(invoiceId), [invoiceId]);
  const [emailOpen, setEmailOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (invoice.loading) {
    return <Loading />;
  }
  if (!invoice.data) {
    return <ErrorMessage message={invoice.error} />;
  }
  const data = invoice.data;
  const canTakePayment = data.status === "OPEN" || data.status === "PARTIALLY_PAID";

  async function run(action: () => Promise<void>) {
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
  }

  function showPdf() {
    run(async () => openBlobInNewTab(await invoiceService.downloadPdf(data.id)));
  }

  function copyShareLink() {
    run(async () => {
      const result = await invoiceService.shareLink(data.id);
      try {
        await navigator.clipboard.writeText(result.url);
        setMessage("Customer link copied: " + result.url);
      } catch {
        setMessage("Customer link: " + result.url);
      }
    });
  }

  async function sendEmail(input: EmailInput) {
    const result = await invoiceService.email(data.id, input);
    setMessage(result.message + " (see Settings → Email log)");
    invoice.reload();
  }

  function voidInvoice() {
    if (!window.confirm("Void invoice " + data.invoice_number + "? This reverses it in your books.")) {
      return;
    }
    run(async () => {
      await invoiceService.void(data.id);
      invoice.reload();
    });
  }

  return (
    <div>
      <PageHeader
        title={"Invoice " + data.invoice_number}
        subtitle={data.last_emailed_at ? "Last emailed " + new Date(data.last_emailed_at).toLocaleString() : undefined}
        actions={
          <>
            <Button variant="secondary" onClick={showPdf}>
              <FileDown size={16} /> PDF
            </Button>
            <Button variant="secondary" onClick={() => setEmailOpen(true)}>
              <Mail size={16} /> Email
            </Button>
            {data.status !== "VOID" && (
              <Button variant="secondary" onClick={copyShareLink}>
                <Link2 size={16} /> Share link
              </Button>
            )}
            {data.status === "OPEN" && toNumber(data.amount_paid) === 0 && (
              <Button variant="danger" onClick={voidInvoice}>
                Void
              </Button>
            )}
            {canTakePayment && (
              <LinkButton href={"/sales/payments/new?customer=" + data.customer.id + "&invoice=" + data.id}>Receive payment</LinkButton>
            )}
          </>
        }
      />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />

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

        <div className="mt-8 grid gap-6 text-sm md:grid-cols-4">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Bill to</div>
            <Link href={"/sales/customers/" + data.customer.id} className="mt-1 block font-medium text-brand-700 hover:underline">
              {data.customer.display_name}
            </Link>
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
          {data.estimate_id && (
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">From estimate</div>
              <Link href={"/sales/forms/estimates/" + data.estimate_id} className="mt-1 block text-brand-700 hover:underline">
                View estimate
              </Link>
            </div>
          )}
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
              <tr key={line.id} className={"border-b border-gray-100 " + (line.is_late_fee ? "text-red-700" : "")}>
                <td className="py-3">{line.description}</td>
                <td className="py-3 text-right">{toNumber(line.quantity)}</td>
                <td className="py-3 text-right">{formatMoney(line.rate, currency)}</td>
                <td className="py-3 text-right">{formatMoney(line.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-6 flex flex-wrap justify-between gap-6">
          <div className="max-w-md whitespace-pre-line text-sm text-gray-600">{data.memo}</div>
          <div className="w-72 space-y-1 text-sm">
            {(toNumber(data.discount_amount) > 0 || toNumber(data.shipping_amount) > 0) && (
              <TotalRow label="Subtotal" value={formatMoney(data.subtotal, currency)} />
            )}
            {toNumber(data.discount_amount) > 0 && (
              <TotalRow
                label={data.discount_type === "PERCENT" ? "Discount (" + toNumber(data.discount_value) + "%)" : "Discount"}
                value={"-" + formatMoney(data.discount_amount, currency)}
              />
            )}
            {toNumber(data.shipping_amount) > 0 && <TotalRow label="Shipping" value={formatMoney(data.shipping_amount, currency)} />}
            <TotalRow label="Total" value={formatMoney(data.total, currency)} />
            <TotalRow label="Amount paid" value={formatMoney(data.amount_paid, currency)} />
            <TotalRow label="Balance due" value={formatMoney(data.balance_due, currency)} bold />
          </div>
        </div>
      </Card>

      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Payments</h2>
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.payment_id}
          emptyText="No payments yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Method", render: (row) => formatLabel(row.payment_method) },
            { header: "Reference", render: (row) => row.reference_no },
            { header: "Deposited to", render: (row) => row.deposit_account.name },
            { header: "Applied", align: "right", render: (row) => formatMoney(row.amount, currency) },
          ]}
        />
      </div>

      <EmailDialog
        key={emailOpen ? "open" : "closed"}
        title={"Email invoice " + data.invoice_number}
        open={emailOpen}
        defaultTo={data.customer.email}
        onClose={() => setEmailOpen(false)}
        onSend={sendEmail}
      />
    </div>
  );
}
