"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { trackingService } from "@/services";
import { NamedListItem } from "@/types/models";

function NewBudgetForm({ classes, locations, onCancel }: { classes: NamedListItem[]; locations: NamedListItem[]; onCancel: () => void }) {
  const router = useRouter();
  const thisYear = new Date().getFullYear();
  const [name, setName] = useState("FY" + thisYear + " budget");
  const [year, setYear] = useState(String(thisYear));
  const [classId, setClassId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const budget = await trackingService.saveBudget({
        name: name,
        fiscal_year: Number(year),
        class_id: classId ? Number(classId) : null,
        location_id: locationId ? Number(locationId) : null,
        lines: [],
      });
      router.push("/accounting/budgets/" + budget.id);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not create the budget.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name" required>
          <TextInput required value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Year" required>
          <TextInput type="number" min="2000" max="2100" required value={year} onChange={(e) => setYear(e.target.value)} />
        </Field>
        {classes.length > 0 && (
          <Field label="Only for class">
            <Select value={classId} onChange={(e) => setClassId(e.target.value)} placeholder="Whole company" options={classes.map((item) => ({ value: item.id, label: item.name }))} />
          </Field>
        )}
        {locations.length > 0 && (
          <Field label="Only for location">
            <Select value={locationId} onChange={(e) => setLocationId(e.target.value)} placeholder="Whole company" options={locations.map((item) => ({ value: item.id, label: item.name }))} />
          </Field>
        )}
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Create</Button>
      </div>
    </form>
  );
}

export default function BudgetsPage() {
  const router = useRouter();
  const budgets = useLoad(() => trackingService.budgets());
  const classes = useLoad(() => trackingService.list("classes"));
  const locations = useLoad(() => trackingService.list("locations"));
  const [open, setOpen] = useState(false);

  if (classes.loading || locations.loading) {
    return <Loading />;
  }
  const names: Record<string, string> = {};
  for (const item of classes.data || []) {
    names["c" + item.id] = item.name;
  }
  for (const item of locations.data || []) {
    names["l" + item.id] = item.name;
  }

  return (
    <div>
      <PageHeader
        title="Budgets"
        subtitle="Plan income and expenses month by month, then compare with what really happened."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New budget
          </Button>
        }
      />
      <ErrorMessage message={budgets.error} />
      <DataTable
        rows={budgets.data || []}
        rowKey={(row) => row.id}
        emptyText="No budgets yet."
        onRowClick={(row) => router.push("/accounting/budgets/" + row.id)}
        columns={[
          { header: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
          { header: "Year", render: (row) => row.fiscal_year },
          {
            header: "For",
            render: (row) => (row.class_id ? "Class: " + names["c" + row.class_id] : row.location_id ? "Location: " + names["l" + row.location_id] : "Whole company"),
          },
        ]}
      />
      <Modal title="New budget" open={open} onClose={() => setOpen(false)}>
        {open && <NewBudgetForm classes={classes.data || []} locations={locations.data || []} onCancel={() => setOpen(false)} />}
      </Modal>
    </div>
  );
}
