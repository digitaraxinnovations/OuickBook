"use client";

import { useParams } from "next/navigation";
import { AttachmentsPanel } from "@/components/ui/AttachmentsPanel";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney } from "@/lib/format";
import { depositService } from "@/services";

/** One bank deposit: the payments and other funds in it, and files attached (e.g. the deposit slip). */
export default function DepositDetailPage() {
  const params = useParams<{ id: string }>();
  const depositId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;
  const deposit = useLoad(() => depositService.get(depositId), [depositId]);

  if (deposit.loading) {
    return <Loading />;
  }
  if (!deposit.data) {
    return <ErrorMessage message={deposit.error} />;
  }
  const data = deposit.data;

  return (
    <div>
      <PageHeader title={"Deposit to " + data.bank_account.name} subtitle={formatDate(data.deposit_date)} />
      <Card>
        <div className="grid gap-6 text-sm md:grid-cols-3">
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Bank account</div>
            <div className="mt-1">{data.bank_account.name}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Date</div>
            <div className="mt-1">{formatDate(data.deposit_date)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Memo</div>
            <div className="mt-1">{data.memo || "-"}</div>
          </div>
        </div>
        <table className="mt-6 w-full text-sm">
          <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2">Source</th>
              <th className="py-2">Account</th>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id} className="border-b border-gray-100">
                <td className="py-2">{formatLabel(line.source_type)}</td>
                <td className="py-2">{line.account.name}</td>
                <td className="py-2">{line.description}</td>
                <td className="py-2 text-right">{formatMoney(line.amount, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 text-right text-lg font-semibold">Total {formatMoney(data.total, currency)}</div>
      </Card>
      <AttachmentsPanel entityType="DEPOSIT" entityId={data.id} />
    </div>
  );
}
