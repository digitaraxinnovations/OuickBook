"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { AgencyForm, CodeForm, RateForm } from "@/components/taxes/TaxSetupForms";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, toNumber } from "@/lib/format";
import { taxService } from "@/services";
import { TaxAgency, TaxCode, TaxRate } from "@/types/models";

type Editing =
  | { kind: "agency"; record: TaxAgency | null }
  | { kind: "rate"; record: TaxRate | null }
  | { kind: "code"; record: TaxCode | null }
  | null;

const MODAL_TITLES = { agency: "Tax agency", rate: "Tax rate", code: "Combined rate" };

function activeText(isActive: boolean) {
  return isActive ? "Active" : <span className="text-gray-400">Inactive</span>;
}

export default function SalesTaxSettingsPage() {
  const agencies = useLoad(() => taxService.agencies());
  const rates = useLoad(() => taxService.rates());
  const codes = useLoad(() => taxService.codes());
  const [editing, setEditing] = useState<Editing>(null);

  if (agencies.loading || rates.loading || codes.loading) {
    return <Loading />;
  }

  const agencyList = agencies.data || [];
  const rateList = rates.data || [];
  const agencyNames: Record<number, string> = {};
  for (const agency of agencyList) {
    agencyNames[agency.id] = agency.name;
  }

  function afterSave() {
    setEditing(null);
    agencies.reload();
    rates.reload();
    codes.reload();
  }

  function close() {
    setEditing(null);
  }

  function editButton(onClick: () => void) {
    return (
      <button onClick={onClick} className="text-sm text-brand-700 hover:underline">
        Edit
      </button>
    );
  }

  return (
    <div>
      <PageHeader title="Sales tax settings" subtitle="Who you collect sales tax for and how much you charge." />
      <ErrorMessage message={agencies.error || rates.error || codes.error} />

      <Card
        title="1. Tax agencies"
        className="mb-6"
        action={
          <Button variant="ghost" onClick={() => setEditing({ kind: "agency", record: null })}>
            <Plus size={16} /> Add agency
          </Button>
        }
      >
        <DataTable
          rows={agencyList}
          rowKey={(row) => row.id}
          emptyText="Add the agency you file sales tax with."
          columns={[
            { header: "Agency", render: (row) => row.name },
            { header: "Files", render: (row) => formatLabel(row.filing_frequency) },
            { header: "Periods start", render: (row) => formatDate(row.start_date) },
            { header: "Liability account", render: (row) => row.liability_account.name },
            { header: "Status", render: (row) => activeText(row.is_active) },
            { header: "Edit", align: "right", render: (row) => editButton(() => setEditing({ kind: "agency", record: row })) },
          ]}
        />
      </Card>

      <Card
        title="2. Tax rates"
        className="mb-6"
        action={
          agencyList.length > 0 ? (
            <Button variant="ghost" onClick={() => setEditing({ kind: "rate", record: null })}>
              <Plus size={16} /> Add rate
            </Button>
          ) : null
        }
      >
        <DataTable
          rows={rateList}
          rowKey={(row) => row.id}
          emptyText={agencyList.length > 0 ? "Add a rate (e.g. State 6%)." : "Add an agency first."}
          columns={[
            { header: "Rate", render: (row) => row.name },
            { header: "Agency", render: (row) => agencyNames[row.agency_id] },
            { header: "Percent", align: "right", render: (row) => toNumber(row.rate) + "%" },
            { header: "Status", render: (row) => activeText(row.is_active) },
            { header: "Edit", align: "right", render: (row) => editButton(() => setEditing({ kind: "rate", record: row })) },
          ]}
        />
      </Card>

      <Card
        title="3. Rates you pick on invoices"
        action={
          rateList.length > 0 ? (
            <Button variant="ghost" onClick={() => setEditing({ kind: "code", record: null })}>
              <Plus size={16} /> Add combined rate
            </Button>
          ) : null
        }
      >
        <p className="mb-3 text-sm text-gray-600">A combined rate adds several rates together, e.g. state 6% + county 1.25% = 7.25%.</p>
        <DataTable
          rows={codes.data || []}
          rowKey={(row) => row.id}
          emptyText="Nothing to pick yet."
          columns={[
            { header: "Name", render: (row) => row.name },
            { header: "Made of", render: (row) => row.components.map((component) => component.name + " " + toNumber(component.rate) + "%").join(" + ") },
            { header: "Total", align: "right", render: (row) => toNumber(row.total_rate) + "%" },
            { header: "Status", render: (row) => activeText(row.is_active) },
            { header: "Edit", align: "right", render: (row) => editButton(() => setEditing({ kind: "code", record: row })) },
          ]}
        />
      </Card>

      <Modal title={editing ? MODAL_TITLES[editing.kind] : ""} open={editing !== null} onClose={close}>
        {editing && editing.kind === "agency" && <AgencyForm initial={editing.record} onSaved={afterSave} onCancel={close} />}
        {editing && editing.kind === "rate" && <RateForm initial={editing.record} agencies={agencyList} onSaved={afterSave} onCancel={close} />}
        {editing && editing.kind === "code" && <CodeForm initial={editing.record} rates={rateList} onSaved={afterSave} onCancel={close} />}
      </Modal>
    </div>
  );
}
