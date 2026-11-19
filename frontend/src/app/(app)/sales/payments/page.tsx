"use client";

import { useRouter } from "next/navigation";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney } from "@/lib/format";
import { paymentService } from "@/services";

export default function PaymentsPage() {
  const { company } = useAuth();
  const router = useRouter();
  const payments = useLoad(() => paymentService.list());

  return (
    <div>
      <PageHeader title="Payments received" subtitle="To receive a payment, open the invoice and click Receive payment." />
      <ErrorMessage message={payments.error} />
      {payments.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push("/sales/invoices/" + row.invoice.id)}
          emptyText="No payments received yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Customer", render: (row) => row.customer.display_name },
            { header: "Invoice", render: (row) => row.invoice.invoice_number },
            { header: "Method", render: (row) => formatLabel(row.payment_method) },
            { header: "Deposited to", render: (row) => row.deposit_account.name },
            { header: "Amount", align: "right", render: (row) => formatMoney(row.amount, company?.currency) },
          ]}
        />
      )}
    </div>
  );
}
