"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { ProjectForm, projectStatusOptions } from "@/components/projects/ProjectForm";
import { Button, LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { customerService, trackingService } from "@/services";

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <Card>
      <div className="text-xs uppercase text-gray-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
      {note && <div className="text-xs text-gray-500">{note}</div>}
    </Card>
  );
}

export default function ProjectPage() {
  const params = useParams();
  const projectId = Number(params.id);
  const { company } = useAuth();
  const currency = company?.currency;
  const summary = useLoad(() => trackingService.projectSummary(projectId), [projectId]);
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const [editOpen, setEditOpen] = useState(false);

  if (summary.loading || customers.loading) {
    return <Loading />;
  }
  if (!summary.data) {
    return <ErrorMessage message={summary.error || "Project not found."} />;
  }
  const data = summary.data;
  const status = projectStatusOptions.find((option) => option.value === data.project.status);

  return (
    <div>
      <PageHeader
        title={data.project.name}
        subtitle={data.customer.display_name + " · " + (status ? status.label : "")}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
            <LinkButton href="/sales/invoices/new">New invoice</LinkButton>
          </div>
        }
      />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Income" value={formatMoney(data.income, currency)} />
        <Tile label="Costs" value={formatMoney(data.costs, currency)} note="Bills, expenses, cost of goods" />
        <Tile label="Labor cost" value={formatMoney(data.labor_cost, currency)} note={toNumber(data.labor_hours) + " hours of time"} />
        <Tile
          label="Profit"
          value={formatMoney(data.profit, currency)}
          note={data.margin_percent !== null ? toNumber(data.margin_percent) + "% margin" : undefined}
        />
      </div>
      {data.project.description && <p className="mb-4 text-sm text-gray-600">{data.project.description}</p>}
      <Card title="Transactions">
        <DataTable
          rows={data.transactions}
          rowKey={(row) => row.entry_date + row.account.id + row.amount + (row.memo || "")}
          emptyText="Nothing on this project yet. Pick the project on an invoice, bill, expense or time entry."
          columns={[
            { header: "Date", render: (row) => formatDate(row.entry_date) },
            { header: "Transaction", render: (row) => row.memo },
            { header: "Account", render: (row) => row.account.name },
            {
              header: "Amount",
              align: "right",
              render: (row) => <span className={toNumber(row.amount) < 0 ? "text-red-600" : ""}>{formatMoney(row.amount, currency)}</span>,
            },
          ]}
        />
      </Card>
      <Modal title="Edit project" open={editOpen} onClose={() => setEditOpen(false)}>
        {editOpen && (
          <ProjectForm
            initial={data.project}
            customers={customers.data || []}
            onSaved={() => {
              setEditOpen(false);
              summary.reload();
            }}
            onCancel={() => setEditOpen(false)}
          />
        )}
      </Modal>
    </div>
  );
}
