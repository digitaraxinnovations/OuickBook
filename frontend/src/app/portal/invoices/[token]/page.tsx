"use client";

import { FileDown } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { portalService } from "@/services";

/** The page a customer sees when they open their invoice link. No sign-in needed. */
export default function CustomerInvoicePage() {
  const params = useParams<{ token: string }>();
  const invoice = useLoad(() => portalService.getInvoice(params.token), [params.token]);
  const [error, setError] = useState<string | null>(null);

  if (invoice.loading) {
    return <Loading />;
  }
  if (!invoice.data) {
    return (
      <div className="mx-auto max-w-xl p-10">
        <ErrorMessage message={invoice.error} />
      </div>
    );
  }
  const data = invoice.data;
  const currency = data.currency;

  async function payNow() {
    setError(null);
    try {
      const result = await portalService.pay(params.token);
      window.location.href = result.checkout_url;
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Online payment is not available.");
    }
  }

  async function downloadPdf() {
    try {
      openBlobInNewTab(await portalService.downloadPdf(params.token));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not open the PDF.");
    }
  }

  return (
    <div className="min-h-screen bg-page px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between rounded-lg bg-white p-6 shadow-sm">
          <div>
            <div className="text-sm text-gray-500">Balance due</div>
            <div className="text-3xl font-semibold">{formatMoney(data.balance_due, currency)}</div>
            <div className="text-sm text-gray-500">Due {formatDate(data.due_date)}</div>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={downloadPdf}>
              <FileDown size={16} /> Download PDF
            </Button>
            {data.online_payment_enabled && <Button onClick={payNow}>Pay now</Button>}
          </div>
        </div>
        <ErrorMessage message={error} />
        {!data.online_payment_enabled && toNumber(data.balance_due) > 0 && (
          <p className="mb-6 text-center text-sm text-gray-500">
            To pay, please contact {data.company_name}
            {data.company_email ? " at " + data.company_email : ""}.
          </p>
        )}

        <div className="rounded-lg bg-white p-8 shadow-sm">
          <div className="flex justify-between gap-6" style={{ borderBottom: "3px solid " + data.accent_color, paddingBottom: 16 }}>
            <div>
              {data.logo_data_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={data.logo_data_url} alt="" className="mb-2 max-h-14" />
              )}
              <div className="text-lg font-semibold">{data.company_name}</div>
              <div className="whitespace-pre-line text-sm text-gray-600">{data.company_address}</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-light uppercase tracking-widest" style={{ color: data.accent_color }}>
                Invoice
              </div>
              <div className="text-sm">No. {data.invoice_number}</div>
              <div className="mt-2">
                <StatusBadge status={data.status} />
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Bill to</div>
              <div className="mt-1">{data.customer_name}</div>
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

          <table className="mt-6 w-full text-sm">
            <thead className="border-b-2 border-gray-200 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2">Description</th>
                <th className="py-2 text-right">Qty</th>
                <th className="py-2 text-right">Rate</th>
                <th className="py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((line, index) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="py-3">{line.description}</td>
                  <td className="py-3 text-right">{toNumber(line.quantity)}</td>
                  <td className="py-3 text-right">{formatMoney(line.rate, currency)}</td>
                  <td className="py-3 text-right">{formatMoney(line.amount, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-6 ml-auto w-64 space-y-1 text-sm">
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
            <div className="flex justify-between">
              <span>Total</span>
              <span>{formatMoney(data.total, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span>Paid</span>
              <span>{formatMoney(data.amount_paid, currency)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-200 pt-2 text-base font-semibold">
              <span>Balance due</span>
              <span>{formatMoney(data.balance_due, currency)}</span>
            </div>
          </div>
          {data.memo && <p className="mt-6 whitespace-pre-line text-sm text-gray-600">{data.memo}</p>}
        </div>
      </div>
    </div>
  );
}
