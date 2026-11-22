"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { PaycheckDialog } from "@/components/payroll/PaycheckDialog";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { SimulatedBadge } from "@/components/ui/SimulatedBadge";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useIntegrations } from "@/hooks/useIntegrations";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { payrollService } from "@/services";
import { Paycheck, PayrollRun } from "@/types/models";

function hoursText(paycheck: Paycheck): string {
  if (paycheck.employee.pay_type === "SALARY") {
    return "Salary";
  }
  let text = toNumber(paycheck.regular_hours) + " h";
  if (toNumber(paycheck.overtime_hours) > 0) {
    text += " + " + toNumber(paycheck.overtime_hours) + " OT";
  }
  return text;
}

export default function PayrollRunPage() {
  const params = useParams();
  const router = useRouter();
  const { company } = useAuth();
  const integrations = useIntegrations();
  const currency = company?.currency;
  const runId = Number(params.id);
  const loaded = useLoad(() => payrollService.run(runId), [runId]);
  const payItems = useLoad(() => payrollService.payItems());
  const [run, setRun] = useState<PayrollRun | null>(null);
  const [editing, setEditing] = useState<Paycheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const current = run || loaded.data;
  if (loaded.loading || payItems.loading) {
    return <Loading />;
  }
  if (!current) {
    return <ErrorMessage message={loaded.error || "Payroll not found."} />;
  }
  const isDraft = current.status === "DRAFT";

  async function act(action: () => Promise<PayrollRun | void>, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await action();
      if (result) {
        setRun(result);
      }
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
    setBusy(false);
  }

  async function deleteDraft() {
    if (!window.confirm("Delete this draft payroll?")) {
      return;
    }
    await payrollService.deleteRun(runId);
    router.push("/payroll/runs");
  }

  async function showStub(paycheck: Paycheck) {
    openBlobInNewTab(await payrollService.payStub(runId, paycheck.id));
  }

  function afterPaycheckSaved(updated: PayrollRun) {
    setRun(updated);
    setEditing(null);
  }

  let totalDeductions = 0;
  let totalTaxes = 0;
  for (const paycheck of current.paychecks) {
    totalDeductions += toNumber(paycheck.employee_deductions);
    totalTaxes += toNumber(paycheck.employee_taxes);
  }

  return (
    <div>
      <PageHeader
        title={"Payroll for " + formatDate(current.pay_date)}
        subtitle={"Pay period " + formatDate(current.period_start) + " - " + formatDate(current.period_end) + " · paid from " + current.bank_account.name}
        actions={
          <div className="flex gap-2">
            {isDraft && (
              <>
                <Button variant="danger" onClick={deleteDraft} disabled={busy}>
                  Delete draft
                </Button>
                <Button onClick={() => act(() => payrollService.approve(runId), "Approve and record this payroll?")} disabled={busy}>
                  Approve payroll
                </Button>
              </>
            )}
            {current.status === "APPROVED" && (
              <Button variant="danger" onClick={() => act(() => payrollService.voidRun(runId), "Void this payroll? Its journal entry is reversed.")} disabled={busy}>
                Void
              </Button>
            )}
          </div>
        }
      />
      <ErrorMessage message={error} />
      {isDraft && (
        <div className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
          This payroll is a draft. Click a paycheck to change hours or amounts, then approve it. Hours come from entered time, or each
          employee&apos;s usual hours.
        </div>
      )}
      {current.status === "VOID" && <div className="mb-4 rounded-md bg-gray-100 p-3 text-sm text-gray-700">This payroll was voided.</div>}

      <div className="mb-6 grid gap-4 sm:grid-cols-4">
        <Card>
          <div className="text-xs uppercase text-gray-500">Gross pay</div>
          <div className="mt-1 text-xl font-semibold">{formatMoney(current.total_gross, currency)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-gray-500">Deductions + taxes</div>
          <div className="mt-1 text-xl font-semibold">{formatMoney(totalDeductions + totalTaxes, currency)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-gray-500">Net pay</div>
          <div className="mt-1 text-xl font-semibold">{formatMoney(current.total_net, currency)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-gray-500">Employer cost</div>
          <div className="mt-1 text-xl font-semibold">{formatMoney(current.total_employer_cost, currency)}</div>
        </Card>
      </div>

      <DataTable
        rows={current.paychecks}
        rowKey={(row) => row.id}
        onRowClick={isDraft ? (row) => setEditing(row) : undefined}
        columns={[
          { header: "Employee", render: (row) => <span className="font-medium">{row.employee.display_name}</span> },
          { header: "Hours", render: (row) => hoursText(row) },
          { header: "Gross", align: "right", render: (row) => formatMoney(row.gross_pay, currency) },
          { header: "Deductions", align: "right", render: (row) => formatMoney(row.employee_deductions, currency) },
          { header: "Taxes", align: "right", render: (row) => formatMoney(row.employee_taxes, currency) },
          { header: "Net pay", align: "right", render: (row) => <strong>{formatMoney(row.net_pay, currency)}</strong> },
          {
            header: "Paid by",
            render: (row) =>
              row.payment_method === "DIRECT_DEPOSIT" ? "Direct deposit" + (row.deposit_reference ? " (" + row.deposit_reference + ")" : "") : row.check_number ? "Check " + row.check_number : "Check",
          },
          {
            header: "Stub",
            align: "right",
            render: (row) => (
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  showStub(row);
                }}
                className="text-sm text-brand-700 hover:underline"
              >
                Pay stub
              </button>
            ),
          },
        ]}
      />
      {current.paychecks.some((paycheck) => paycheck.payment_method === "DIRECT_DEPOSIT") && current.status === "APPROVED" && (
        <p className="mt-3 text-sm text-gray-600">
          {integrations?.payroll.enabled ? (
            <>
              Direct deposits were sent by the payroll service; each reference is shown under Paid by.
              {integrations.payroll.simulated && <SimulatedBadge title="Simulated: no money was sent; the references are made up." />}
            </>
          ) : (
            "No payroll service is connected, so direct deposit pay is recorded but not sent. Send it from your bank."
          )}
        </p>
      )}
      {editing && (
        <PaycheckDialog runId={runId} paycheck={editing} payItems={payItems.data || []} onClose={() => setEditing(null)} onSaved={afterPaycheckSaved} />
      )}
    </div>
  );
}
