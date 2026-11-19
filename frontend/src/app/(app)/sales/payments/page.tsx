"use client";

import { Plus } from "lucide-react";
import { LinkButton } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { paymentService } from "@/services";
import { Payment } from "@/types/models";

function appliedTo(payment: Payment): string {
  if (payment.applications.length === 0) {
    return "Not applied (customer credit)";
  }
  return payment.applications.map((item) => "Invoice " + item.invoice.invoice_number).join(", ");
}

export default function PaymentsPage() {
  const { company } = useAuth();
  const currency = company?.currency;
  const payments = useLoad(() => paymentService.list());

  return (
    <div>
      <PageHeader
        title="Payments received"
        actions={
          <LinkButton href="/sales/payments/new">
            <Plus size={16} /> Receive payment
          </LinkButton>
        }
      />
      <ErrorMessage message={payments.error} />
      {payments.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.id}
          emptyText="No payments received yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Customer", render: (row) => row.customer.display_name },
            { header: "Applied to", render: (row) => appliedTo(row) },
            { header: "Method", render: (row) => formatLabel(row.payment_method) },
            { header: "Deposited to", render: (row) => row.deposit_account.name + (row.deposit_id ? " (deposited)" : "") },
            {
              header: "Unapplied",
              align: "right",
              render: (row) => (toNumber(row.unapplied_amount) > 0 ? formatMoney(row.unapplied_amount, currency) : ""),
            },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, currency) },
          ]}
        />
      )}
    </div>
  );
}
