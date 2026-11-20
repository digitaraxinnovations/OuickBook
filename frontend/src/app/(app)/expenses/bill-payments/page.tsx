"use client";

import { Printer, Trash2 } from "lucide-react";
import { useState } from "react";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatLabel, formatMoney } from "@/lib/format";
import { billPaymentService, checkService } from "@/services";
import { BillPayment } from "@/types/models";

function billsPaid(payment: BillPayment): string {
  return payment.applications.map((item) => "Bill " + (item.bill.doc_number || "#" + item.bill.id)).join(", ");
}

export default function BillPaymentsPage() {
  const { company } = useAuth();
  const payments = useLoad(() => billPaymentService.list());
  const [error, setError] = useState<string | null>(null);

  async function remove(payment: BillPayment) {
    if (!window.confirm("Delete this bill payment? The bills become unpaid again.")) {
      return;
    }
    setError(null);
    try {
      await billPaymentService.remove(payment.id);
      payments.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not delete.");
    }
  }

  async function reprint(payment: BillPayment) {
    try {
      openBlobInNewTab(await checkService.reprint("BILL_PAYMENT", payment.id));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not print.");
    }
  }

  return (
    <div>
      <PageHeader title="Bill payments" actions={<LinkButton href="/expenses/pay-bills">Pay bills</LinkButton>} />
      <ErrorMessage message={error || payments.error} />
      {payments.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.id}
          emptyText="No bill payments yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Vendor", render: (row) => row.vendor.display_name },
            { header: "Bills", render: (row) => billsPaid(row) },
            {
              header: "Method",
              render: (row) =>
                formatLabel(row.payment_method) + (row.check_number ? " #" + row.check_number : row.print_later ? " (to print)" : ""),
            },
            { header: "Paid from", render: (row) => row.payment_account.name },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, company?.currency) },
            {
              header: "",
              align: "right",
              render: (row) => (
                <span className="flex justify-end gap-3 text-gray-400">
                  {row.check_number && (
                    <button onClick={() => reprint(row)} className="hover:text-brand-700" title="Print check">
                      <Printer size={16} />
                    </button>
                  )}
                  <button onClick={() => remove(row)} className="hover:text-red-600" title="Delete payment">
                    <Trash2 size={16} />
                  </button>
                </span>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
