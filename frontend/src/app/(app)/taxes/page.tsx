"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { PayTaxDialog } from "@/components/taxes/PayTaxDialog";
import { TaxAdjustmentDialog } from "@/components/taxes/TaxAdjustmentDialog";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useIntegrations } from "@/hooks/useIntegrations";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { accountService, taxService } from "@/services";
import { TaxPeriod, TaxPeriodStatus } from "@/types/models";
import { appConfig } from "@/config/app.config";

const STATUS_STYLES: Record<TaxPeriodStatus, string> = {
  OPEN: "bg-blue-50 text-blue-700",
  DUE: "bg-amber-50 text-amber-800",
  PAID: "bg-green-50 text-green-700",
  NOTHING_DUE: "bg-gray-100 text-gray-600",
};

const STATUS_LABELS: Record<TaxPeriodStatus, string> = {
  OPEN: "Open",
  DUE: "Due",
  PAID: "Paid",
  NOTHING_DUE: "Nothing due",
};

function StatusBadge({ status }: { status: TaxPeriodStatus }) {
  return <span className={"whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium " + STATUS_STYLES[status]}>{STATUS_LABELS[status]}</span>;
}

export default function SalesTaxPage() {
  const { company } = useAuth();
  const currency = company?.currency;
  const periods = useLoad(() => taxService.periods());
  const agencies = useLoad(() => taxService.agencies());
  const payments = useLoad(() => taxService.payments());
  const adjustments = useLoad(() => taxService.adjustments());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [payOpen, setPayOpen] = useState(false);
  const [payPeriod, setPayPeriod] = useState<TaxPeriod | null>(null);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [fileMode, setFileMode] = useState(false);
  const integrations = useIntegrations();
  const canEFile = integrations?.tax_rates.enabled ?? false;
  const openPayFromMenu = useQueryFlag("pay");

  useEffect(() => {
    if (openPayFromMenu) {
      setPayOpen(true);
    }
  }, [openPayFromMenu]);

  if (periods.loading || agencies.loading || accounts.loading) {
    return <Loading />;
  }

  const allPeriods = periods.data || [];
  const duePeriods = allPeriods.filter((period) => period.status === "DUE");
  let totalDue = 0;
  for (const period of duePeriods) {
    totalDue += toNumber(period.balance);
  }
  let openCollected = 0;
  for (const period of allPeriods) {
    if (period.status === "OPEN") {
      openCollected += toNumber(period.balance);
    }
  }

  const agencyNames: Record<number, string> = {};
  for (const agency of agencies.data || []) {
    agencyNames[agency.id] = agency.name;
  }

  function startPayment(period: TaxPeriod | null, eFile = false) {
    setPayPeriod(period);
    setFileMode(eFile);
    setPayOpen(true);
  }

  function afterSave() {
    setPayOpen(false);
    setAdjustOpen(false);
    periods.reload();
    payments.reload();
    adjustments.reload();
  }

  if ((agencies.data || []).length === 0) {
    return (
      <div>
        <PageHeader title="Sales tax" />
        <Card>
          <p className="mb-4 text-sm text-gray-600">
            Add the agency you collect sales tax for and its rates. Then pick a rate on your invoices and {appConfig.appName} keeps track of what you owe.
          </p>
          <LinkButton href="/taxes/settings">Set up sales tax</LinkButton>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Sales tax"
        subtitle="What you owe each agency, per filing period."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setAdjustOpen(true)}>
              Add adjustment
            </Button>
            <Button onClick={() => startPayment(null)}>
              <Plus size={16} /> Record payment
            </Button>
          </div>
        }
      />
      <ErrorMessage message={periods.error} />

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <Card>
          <div className="text-xs uppercase text-gray-500">Due now</div>
          <div className="mt-1 text-2xl font-semibold">{formatMoney(totalDue, currency)}</div>
          <div className="text-xs text-gray-500">{duePeriods.length} period(s) ended and not fully paid</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-gray-500">Collected in open periods</div>
          <div className="mt-1 text-2xl font-semibold">{formatMoney(openCollected, currency)}</div>
          <div className="text-xs text-gray-500">Due once the current period ends</div>
        </Card>
      </div>

      <Card title="Filing periods" className="mb-6">
        <DataTable
          rows={allPeriods}
          rowKey={(row) => row.agency_id + row.period_start}
          emptyText="No filing periods yet."
          columns={[
            { header: "Agency", render: (row) => row.agency_name },
            {
              header: "Period",
              render: (row) => (
                <span className="whitespace-nowrap">
                  {formatDate(row.period_start)} - {formatDate(row.period_end)}
                </span>
              ),
            },
            { header: "Collected", align: "right", render: (row) => formatMoney(row.tax_collected, currency) },
            { header: "Adjustments", align: "right", render: (row) => formatMoney(row.adjustments, currency) },
            { header: "Payments", align: "right", render: (row) => formatMoney(row.payments, currency) },
            { header: "Balance", align: "right", render: (row) => <strong>{formatMoney(row.balance, currency)}</strong> },
            { header: "Status", render: (row) => <StatusBadge status={row.status} /> },
            {
              header: "Action",
              align: "right",
              render: (row) =>
                row.status === "DUE" ? (
                  <span className="flex justify-end gap-3">
                    {canEFile && (
                      <button onClick={() => startPayment(row, true)} className="text-sm font-medium text-brand-700 hover:underline">
                        File return
                      </button>
                    )}
                    <button onClick={() => startPayment(row)} className="text-sm font-medium text-brand-700 hover:underline">
                      Pay
                    </button>
                  </span>
                ) : null,
            },
          ]}
        />
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Payments">
          <DataTable
            rows={payments.data || []}
            rowKey={(row) => row.id}
            emptyText="No sales tax payments yet."
            columns={[
              { header: "Date", render: (row) => formatDate(row.payment_date) },
              { header: "Agency", render: (row) => agencyNames[row.agency_id] },
              { header: "For period", render: (row) => formatDate(row.period_start) + " - " + formatDate(row.period_end) },
              { header: "Confirmation", render: (row) => row.confirmation_no || "" },
              { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
            ]}
          />
        </Card>
        <Card title="Adjustments">
          <DataTable
            rows={adjustments.data || []}
            rowKey={(row) => row.id}
            emptyText="No adjustments yet."
            columns={[
              { header: "Date", render: (row) => formatDate(row.adjustment_date) },
              { header: "Agency", render: (row) => agencyNames[row.agency_id] },
              { header: "Reason", render: (row) => row.reason },
              { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
            ]}
          />
        </Card>
      </div>

      {payOpen && (
        <PayTaxDialog
          open={payOpen}
          period={payPeriod}
          duePeriods={duePeriods}
          accounts={accounts.data || []}
          eFile={fileMode}
          simulated={integrations?.tax_rates.simulated ?? false}
          onClose={() => setPayOpen(false)}
          onSaved={afterSave}
        />
      )}
      {adjustOpen && (
        <TaxAdjustmentDialog
          open={adjustOpen}
          agencies={agencies.data || []}
          accounts={accounts.data || []}
          onClose={() => setAdjustOpen(false)}
          onSaved={afterSave}
        />
      )}
    </div>
  );
}
