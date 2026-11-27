"use client";

import { FileDown, Mail, Pencil, Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ContactForm } from "@/components/forms/ContactForm";
import { EmailDialog } from "@/components/sales/EmailDialog";
import { ScoreNote } from "@/components/sales/ScoreBadge";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, StatusBadge, SuccessMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { findFormByType } from "@/config/sales-forms.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatLabel, formatMoney, todayString } from "@/lib/format";
import { customerService, invoiceService, platformService, salesDocumentService, taxService, termsService } from "@/services";
import { ContactInput, EmailInput } from "@/types/inputs";
import { StatementType } from "@/types/models";

const statementTypeOptions = [
  { value: "BALANCE_FORWARD", label: "Balance forward" },
  { value: "OPEN_ITEM", label: "Open item (unpaid invoices)" },
  { value: "TRANSACTION", label: "Transaction statement" },
];

function firstOfMonth(): string {
  return todayString().substring(0, 8) + "01";
}

/** One row in the customer's transaction list. */
interface ActivityRow {
  key: string;
  date: string;
  type: string;
  number: string;
  status: string;
  overdue: boolean;
  total: string;
  href: string;
}

async function loadActivity(customerId: number): Promise<ActivityRow[]> {
  const rows: ActivityRow[] = [];
  const invoices = await invoiceService.listSummaries({ customer_id: customerId });
  for (const invoice of invoices) {
    rows.push({
      key: "invoice-" + invoice.id,
      date: invoice.invoice_date,
      type: "Invoice",
      number: invoice.invoice_number,
      status: invoice.status,
      overdue: invoice.is_overdue,
      total: invoice.total,
      href: "/sales/invoices/" + invoice.id,
    });
  }
  const documents = await salesDocumentService.list({ customer_id: customerId });
  for (const document of documents) {
    const form = findFormByType(document.doc_type);
    rows.push({
      key: "doc-" + document.id,
      date: document.doc_date,
      type: form.title,
      number: document.doc_number,
      status: document.status,
      overdue: false,
      total: document.total,
      href: "/sales/forms/" + form.slug + "/" + document.id,
    });
  }
  rows.sort((a, b) => (a.date < b.date ? 1 : -1));
  return rows;
}

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = Number(params.id);
  const router = useRouter();
  const { company } = useAuth();
  const currency = company?.currency;

  const customer = useLoad(() => customerService.get(customerId), [customerId]);
  const activity = useLoad(() => loadActivity(customerId), [customerId]);
  const terms = useLoad(() => termsService.list());
  const taxCodes = useLoad(() => taxService.codes(true));
  const currencies = useLoad(() => platformService.currencies());
  const score = useLoad(() => customerService.paymentScore(customerId), [customerId]);

  const [statementType, setStatementType] = useState<StatementType>("BALANCE_FORWARD");
  const [startDate, setStartDate] = useState(firstOfMonth());
  const [endDate, setEndDate] = useState(todayString());
  const statement = useLoad(
    () => customerService.statement(customerId, statementType, startDate, endDate),
    [customerId, statementType, startDate, endDate],
  );

  const [editOpen, setEditOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (customer.loading) {
    return <Loading />;
  }
  if (!customer.data) {
    return <ErrorMessage message={customer.error} />;
  }
  const data = customer.data;

  async function saveCustomer(input: ContactInput) {
    await customerService.update(data.id, input);
    setEditOpen(false);
    customer.reload();
  }

  async function showStatementPdf() {
    setError(null);
    try {
      openBlobInNewTab(await customerService.statementPdf(data.id, statementType, startDate, endDate));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not create the PDF.");
    }
  }

  async function emailStatement(input: EmailInput) {
    const result = await customerService.emailStatement(data.id, {
      ...input,
      statement_type: statementType,
      start_date: startDate,
      end_date: endDate,
    });
    setMessage(result.message);
  }

  return (
    <div>
      <PageHeader
        title={data.display_name}
        subtitle={[data.company_name, data.email, data.phone].filter(Boolean).join(" · ")}
        actions={
          <>
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              <Pencil size={16} /> Edit
            </Button>
            <LinkButton href={"/sales/payments/new?customer=" + data.id} variant="secondary">
              Receive payment
            </LinkButton>
            <Button onClick={() => router.push("/sales/invoices/new")}>
              <Plus size={16} /> New invoice
            </Button>
          </>
        }
      />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Open balance</div>
          <div className="mt-1 text-2xl font-semibold">{formatMoney(data.open_balance, currency)}</div>
        </Card>
        <Card className="md:col-span-2">
          <div className="text-xs font-semibold uppercase text-gray-500">Billing address</div>
          <div className="mt-1 whitespace-pre-line text-sm">{data.address || "-"}</div>
        </Card>
      </div>

      {score.data && (
        <Card className="mb-6">
          <div className="mb-2 text-xs font-semibold uppercase text-gray-500">How this customer pays</div>
          <ScoreNote score={score.data} />
        </Card>
      )}

      <h2 className="mb-3 text-lg font-semibold">Transactions</h2>
      {activity.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={activity.data || []}
          rowKey={(row) => row.key}
          onRowClick={(row) => router.push(row.href)}
          emptyText="No transactions with this customer yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.date) },
            { header: "Type", render: (row) => row.type },
            { header: "No.", render: (row) => row.number },
            { header: "Status", render: (row) => <StatusBadge status={row.status} overdue={row.overdue} /> },
            { header: "Total", align: "right", render: (row) => formatMoney(row.total, currency) },
          ]}
        />
      )}

      <h2 className="mt-10 mb-3 text-lg font-semibold">Statement</h2>
      <Card>
        <div className="mb-4 flex flex-wrap items-end gap-4">
          <div className="w-60">
            <Field label="Statement type">
              <Select value={statementType} onChange={(e) => setStatementType(e.target.value as StatementType)} options={statementTypeOptions} />
            </Field>
          </div>
          {statementType !== "OPEN_ITEM" && (
            <div className="w-44">
              <Field label="From">
                <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </Field>
            </div>
          )}
          <div className="w-44">
            <Field label={statementType === "OPEN_ITEM" ? "As of" : "To"}>
              <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </Field>
          </div>
          <div className="ml-auto flex gap-2">
            <Button variant="secondary" onClick={showStatementPdf}>
              <FileDown size={16} /> PDF
            </Button>
            <Button variant="secondary" onClick={() => setEmailOpen(true)}>
              <Mail size={16} /> Email
            </Button>
          </div>
        </div>
        <ErrorMessage message={statement.error} />
        {statement.data && (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2">Date</th>
                <th className="py-2">Transaction</th>
                <th className="py-2">Reference</th>
                <th className="py-2 text-right">Amount</th>
                <th className="py-2 text-right">Balance</th>
              </tr>
            </thead>
            <tbody>
              {statement.data.statement_type === "BALANCE_FORWARD" && (
                <tr className="border-b border-gray-100 text-gray-600">
                  <td className="py-2">{formatDate(statement.data.start_date)}</td>
                  <td className="py-2">Balance forward</td>
                  <td></td>
                  <td></td>
                  <td className="py-2 text-right">{formatMoney(statement.data.opening_balance, currency)}</td>
                </tr>
              )}
              {statement.data.lines.map((line, index) => (
                <tr key={index} className="border-b border-gray-100">
                  <td className="py-2">{formatDate(line.line_date)}</td>
                  <td className="py-2">{line.transaction_type}</td>
                  <td className="py-2">{line.reference}</td>
                  <td className="py-2 text-right">{formatMoney(line.amount, currency)}</td>
                  <td className="py-2 text-right">{formatMoney(line.balance, currency)}</td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td colSpan={4} className="py-3 text-right">
                  {formatLabel(statement.data.statement_type)} - amount due
                </td>
                <td className="py-3 text-right">{formatMoney(statement.data.closing_balance, currency)}</td>
              </tr>
            </tbody>
          </table>
        )}
      </Card>

      <Modal title="Edit customer" open={editOpen} onClose={() => setEditOpen(false)}>
        <ContactForm key={data.id + "-" + editOpen} initial={data} terms={terms.data || []} taxCodes={taxCodes.data || []} currencies={currencies.data || []} onSave={saveCustomer} onCancel={() => setEditOpen(false)} />
      </Modal>
      <EmailDialog
        key={emailOpen ? "open" : "closed"}
        title="Email statement"
        open={emailOpen}
        defaultTo={data.email}
        onClose={() => setEmailOpen(false)}
        onSend={emailStatement}
      />
    </div>
  );
}
