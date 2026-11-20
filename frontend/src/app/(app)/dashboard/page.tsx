"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { LinkButton } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { invoiceService, reportService } from "@/services";

function BigNumber({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  const color = tone === "good" ? "text-brand-700" : tone === "bad" ? "text-red-600" : "text-gray-900";
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className={"mt-1 text-2xl font-semibold " + color}>{value}</div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, company } = useAuth();
  const summary = useLoad(() => reportService.getDashboard());
  const invoices = useLoad(() => invoiceService.listSummaries());
  const currency = company?.currency;

  if (summary.loading) {
    return <Loading />;
  }
  if (!summary.data) {
    return <ErrorMessage message={summary.error} />;
  }
  const data = summary.data;
  const recentInvoices = (invoices.data || []).slice(0, 5);

  return (
    <div>
      <PageHeader
        title={"Welcome back, " + (user?.full_name.split(" ")[0] || "")}
        subtitle={"Year to date: " + formatDate(data.period_start) + " - " + formatDate(data.period_end)}
        actions={
          <>
            <LinkButton href="/sales/invoices/new">Create invoice</LinkButton>
            <LinkButton href="/expenses/new" variant="secondary">
              Record expense
            </LinkButton>
          </>
        }
      />

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Profit & loss">
          <div className="space-y-4">
            <BigNumber label="Net income" value={formatMoney(data.net_income, currency)} tone={toNumber(data.net_income) >= 0 ? "good" : "bad"} />
            <div className="grid grid-cols-2 gap-4">
              <BigNumber label="Income" value={formatMoney(data.income, currency)} />
              <BigNumber label="Expenses" value={formatMoney(data.expenses, currency)} />
            </div>
          </div>
        </Card>

        <Card title="Invoices">
          <div className="space-y-4">
            <BigNumber label={"Unpaid (" + data.open_invoice_count + ")"} value={formatMoney(data.open_invoices_total, currency)} />
            <BigNumber
              label={"Overdue (" + data.overdue_invoice_count + ")"}
              value={formatMoney(data.overdue_invoices_total, currency)}
              tone={data.overdue_invoice_count > 0 ? "bad" : undefined}
            />
          </div>
        </Card>

        <Card title="Bills to pay">
          <div className="space-y-4">
            <BigNumber label="Unpaid" value={formatMoney(data.unpaid_bills_total, currency)} />
            <BigNumber
              label={"Overdue (" + data.overdue_bill_count + ")"}
              value={formatMoney(data.overdue_bills_total, currency)}
              tone={data.overdue_bill_count > 0 ? "bad" : undefined}
            />
          </div>
        </Card>

        <Card title="Bank accounts">
          {data.bank_accounts.length === 0 && <p className="text-sm text-gray-500">No bank activity yet.</p>}
          <ul className="divide-y divide-gray-100">
            {data.bank_accounts.map((account) => (
              <li key={account.account_id} className="flex justify-between py-2 text-sm">
                <span>{account.name}</span>
                <span className="font-medium">{formatMoney(account.balance, currency)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent invoices</h2>
          <Link href="/sales/invoices" className="text-sm font-medium text-brand-700 hover:underline">
            View all
          </Link>
        </div>
        <DataTable
          rows={recentInvoices}
          rowKey={(row) => row.id}
          emptyText="No invoices yet. Create your first one!"
          columns={[
            { header: "No.", render: (row) => <Link className="text-brand-700 hover:underline" href={"/sales/invoices/" + row.id}>{row.invoice_number}</Link> },
            { header: "Customer", render: (row) => row.customer.display_name },
            { header: "Date", render: (row) => formatDate(row.invoice_date) },
            { header: "Status", render: (row) => <StatusBadge status={row.status} overdue={row.is_overdue} /> },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.total, currency) },
          ]}
        />
      </div>
    </div>
  );
}
