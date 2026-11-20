"use client";

import { FileDown, Mail } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { EmailDialog } from "@/components/sales/EmailDialog";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading, StatusBadge, SuccessMessage } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { findFormBySlug } from "@/config/sales-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatLabel, formatMoney, todayString, toNumber } from "@/lib/format";
import { salesDocumentService } from "@/services";
import { EmailInput } from "@/types/inputs";
import { SalesDocStatus } from "@/types/models";

/** Detail page shared by every sales form type. */
export default function SalesFormDetailPage() {
  const params = useParams<{ slug: string; id: string }>();
  const form = findFormBySlug(params.slug);
  const documentId = Number(params.id);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;

  const document = useLoad(() => salesDocumentService.get(documentId), [documentId]);
  const [emailOpen, setEmailOpen] = useState(false);
  const [convertOpen, setConvertOpen] = useState(false);
  const [percent, setPercent] = useState("100");
  const [invoiceDate, setInvoiceDate] = useState(todayString());
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

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
  const isEstimate = data.doc_type === "ESTIMATE";
  const canConvert = isEstimate && (data.status === "PENDING" || data.status === "ACCEPTED");

  async function run(action: () => Promise<void>) {
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
  }

  function setStatus(status: SalesDocStatus) {
    run(async () => {
      await salesDocumentService.setEstimateStatus(data.id, status);
      document.reload();
    });
  }

  function voidDocument() {
    if (!window.confirm("Void this " + config.title.toLowerCase() + "?")) {
      return;
    }
    run(async () => {
      await salesDocumentService.void(data.id);
      document.reload();
    });
  }

  async function sendEmail(input: EmailInput) {
    const result = await salesDocumentService.email(data.id, input);
    setMessage(result.message);
    document.reload();
  }

  function convert() {
    run(async () => {
      const invoice = await salesDocumentService.convertToInvoice(data.id, invoiceDate, percent);
      router.push("/sales/invoices/" + invoice.id);
    });
  }

  return (
    <div>
      <PageHeader
        title={form.title + " " + data.doc_number}
        actions={
          <>
            <Button variant="secondary" onClick={() => run(async () => openBlobInNewTab(await salesDocumentService.downloadPdf(data.id)))}>
              <FileDown size={16} /> PDF
            </Button>
            <Button variant="secondary" onClick={() => setEmailOpen(true)}>
              <Mail size={16} /> Email
            </Button>
            {isEstimate && data.status === "PENDING" && (
              <>
                <Button variant="secondary" onClick={() => setStatus("ACCEPTED")}>
                  Mark accepted
                </Button>
                <Button variant="secondary" onClick={() => setStatus("REJECTED")}>
                  Mark rejected
                </Button>
              </>
            )}
            {isEstimate && data.status === "REJECTED" && (
              <Button variant="secondary" onClick={() => setStatus("PENDING")}>
                Reopen
              </Button>
            )}
            {data.status !== "VOID" && toNumber(data.amount_applied) === 0 && !data.invoice_id && !data.deposit_id && (
              <Button variant="danger" onClick={voidDocument}>
                Void
              </Button>
            )}
            {canConvert && <Button onClick={() => setConvertOpen(true)}>Create invoice</Button>}
          </>
        }
      />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="grid gap-6 text-sm sm:grid-cols-3">
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Customer</div>
              <Link href={"/sales/customers/" + data.customer.id} className="mt-1 block font-medium text-brand-700 hover:underline">
                {data.customer.display_name}
              </Link>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Date</div>
              <div className="mt-1">{formatDate(data.doc_date)}</div>
            </div>
            {data.expiration_date && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">Expires</div>
                <div className="mt-1">{formatDate(data.expiration_date)}</div>
              </div>
            )}
            {data.money_account && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">
                  {data.doc_type === "REFUND_RECEIPT" ? "Refunded from" : "Deposited to"}
                </div>
                <div className="mt-1">{data.money_account.name}</div>
              </div>
            )}
            {data.payment_method && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">Payment method</div>
                <div className="mt-1">{formatLabel(data.payment_method)}</div>
              </div>
            )}
            {data.invoice_id && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500">Added to</div>
                <Link href={"/sales/invoices/" + data.invoice_id} className="mt-1 block text-brand-700 hover:underline">
                  View invoice
                </Link>
              </div>
            )}
          </div>
          <StatusBadge status={data.status} />
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

        <div className="mt-6 flex flex-wrap justify-between gap-6">
          <div className="max-w-md whitespace-pre-line text-sm text-gray-600">{data.memo}</div>
          <div className="w-72 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{formatMoney(data.subtotal, currency)}</span>
            </div>
            {toNumber(data.discount_amount) > 0 && (
              <div className="flex justify-between">
                <span>Discount</span>
                <span>-{formatMoney(data.discount_amount, currency)}</span>
              </div>
            )}
            {toNumber(data.shipping_amount) > 0 && (
              <div className="flex justify-between">
                <span>Shipping</span>
                <span>{formatMoney(data.shipping_amount, currency)}</span>
              </div>
            )}
            {data.tax_code_id !== null && (
              <div className="flex justify-between">
                <span>Sales tax</span>
                <span>{formatMoney(data.tax_amount, currency)}</span>
              </div>
            )}
            <div className="flex justify-between border-t border-gray-200 pt-2 text-base font-semibold">
              <span>Total</span>
              <span>{formatMoney(data.total, currency)}</span>
            </div>
            {(isEstimate || data.doc_type === "CREDIT_MEMO") && (
              <div className="flex justify-between text-gray-600">
                <span>{isEstimate ? "Not yet invoiced" : "Credit remaining"}</span>
                <span>{formatMoney(data.remaining, currency)}</span>
              </div>
            )}
          </div>
        </div>
      </Card>

      <EmailDialog
        key={emailOpen ? "open" : "closed"}
        title={"Email " + form.title.toLowerCase() + " " + data.doc_number}
        open={emailOpen}
        defaultTo={data.customer.email}
        onClose={() => setEmailOpen(false)}
        onSend={sendEmail}
      />

      <Modal title="Create invoice from estimate" open={convertOpen} onClose={() => setConvertOpen(false)}>
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Invoice the whole estimate, or only part of it now (progress invoicing). Left to invoice:{" "}
            <strong>{formatMoney(data.remaining, currency)}</strong>
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Percent of estimate">
              <TextInput type="number" min="1" max="100" step="0.01" value={percent} onChange={(e) => setPercent(e.target.value)} />
            </Field>
            <Field label="Invoice date">
              <TextInput type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
            </Field>
          </div>
          <p className="text-sm">
            This invoice: about <strong>{formatMoney((toNumber(data.total) * toNumber(percent)) / 100, currency)}</strong>
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConvertOpen(false)}>
              Cancel
            </Button>
            <Button onClick={convert}>Create invoice</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
