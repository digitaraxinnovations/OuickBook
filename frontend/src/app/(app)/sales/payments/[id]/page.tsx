"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { AttachmentsPanel } from "@/components/ui/AttachmentsPanel";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { paymentService } from "@/services";

/** One customer payment: what it paid, where it went, and files attached (e.g. a scan of the check). */
export default function PaymentDetailPage() {
  const params = useParams<{ id: string }>();
  const paymentId = Number(params.id);
  const { company } = useAuth();
  const payment = useLoad(() => paymentService.get(paymentId), [paymentId]);

  if (payment.loading) {
    return <Loading />;
  }
  if (!payment.data) {
    return <ErrorMessage message={payment.error} />;
  }
  const data = payment.data;
  const currency = data.currency_code || company?.currency;

  return (
    <div>
      <PageHeader title={"Payment from " + data.customer.display_name} subtitle={formatDate(data.payment_date)} />
      <Card>
        <div className="grid gap-6 text-sm md:grid-cols-4">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Customer</div>
            <Link href={"/sales/customers/" + data.customer.id} className="mt-1 block text-brand-700 hover:underline">
              {data.customer.display_name}
            </Link>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Method</div>
            <div className="mt-1">
              {formatLabel(data.payment_method)}
              {data.reference_no ? " - " + data.reference_no : ""}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Deposited to</div>
            <div className="mt-1">
              {data.deposit_account.name}
              {data.deposit_id ? " (deposited)" : ""}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Amount</div>
            <div className="mt-1 text-lg font-semibold">{formatMoney(data.amount, currency)}</div>
          </div>
        </div>
        <table className="mt-6 w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Applied to</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.applications.map((item) => (
              <tr key={item.invoice.id} className="border-b border-gray-100">
                <td className="py-2">
                  <Link href={"/sales/invoices/" + item.invoice.id} className="text-brand-700 hover:underline">
                    Invoice {item.invoice.invoice_number}
                  </Link>
                </td>
                <td className="py-2 text-right">{formatMoney(item.amount, currency)}</td>
              </tr>
            ))}
            {data.credits_used.map((credit) => (
              <tr key={credit.source_type + credit.source_id} className="border-b border-gray-100">
                <td className="py-2">Credit used ({formatLabel(credit.source_type)})</td>
                <td className="py-2 text-right">{formatMoney(credit.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 flex justify-between text-sm">
          <div className="text-gray-600">{data.memo}</div>
          {toNumber(data.unapplied_amount) > 0 && <div>Left as credit: {formatMoney(data.unapplied_amount, currency)}</div>}
        </div>
      </Card>
      <AttachmentsPanel entityType="PAYMENT" entityId={data.id} />
    </div>
  );
}
