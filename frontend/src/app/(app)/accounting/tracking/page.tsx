"use client";

import { Plus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { trackingService } from "@/services";
import { NamedListItem, Tag } from "@/types/models";

type ListKind = "classes" | "locations";

const LABELS: Record<ListKind, string> = { classes: "class", locations: "location" };

function NamedItemForm({ kind, initial, items, onSaved, onCancel }: {
  kind: ListKind;
  initial: NamedListItem | null;
  items: NamedListItem[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [parentId, setParentId] = useState(initial && initial.parent_id ? String(initial.parent_id) : "");
  const [isActive, setIsActive] = useState(initial ? initial.is_active : true);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await trackingService.save(kind, { name: name, parent_id: parentId ? Number(parentId) : null, is_active: isActive }, initial?.id);
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <Field label="Name" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label={"Inside " + LABELS[kind]}>
        <Select
          value={parentId}
          onChange={(e) => setParentId(e.target.value)}
          placeholder="(top level)"
          options={items.filter((item) => item.id !== initial?.id).map((item) => ({ value: item.id, label: item.name }))}
        />
      </Field>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}

function TagForm({ initial, onSaved, onCancel }: { initial: Tag | null; onSaved: () => void; onCancel: () => void }) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [groupName, setGroupName] = useState(initial?.group_name || "");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await trackingService.saveTag({ name: name, group_name: groupName }, initial?.id);
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <Field label="Tag" required>
        <TextInput required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Spring promo" />
      </Field>
      <Field label="Group">
        <TextInput value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="e.g. Campaigns" />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save</Button>
      </div>
    </form>
  );
}

type Editing = { kind: ListKind; record: NamedListItem | null } | { kind: "tags"; record: Tag | null } | null;

function NamedListCard({ kind, title, help, items, onEdit }: {
  kind: ListKind;
  title: string;
  help: string;
  items: NamedListItem[];
  onEdit: (record: NamedListItem | null) => void;
}) {
  const names: Record<number, string> = {};
  for (const item of items) {
    names[item.id] = item.name;
  }
  return (
    <Card
      title={title}
      action={
        <Button variant="ghost" onClick={() => onEdit(null)}>
          <Plus size={16} /> Add
        </Button>
      }
    >
      <p className="mb-3 text-sm text-gray-600">{help}</p>
      <DataTable
        rows={items}
        rowKey={(row) => row.id}
        emptyText={"No " + kind + " yet."}
        onRowClick={(row) => onEdit(row)}
        columns={[
          { header: "Name", render: (row) => (row.parent_id ? names[row.parent_id] + " : " : "") + row.name },
          { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
        ]}
      />
    </Card>
  );
}

export default function TrackingSetupPage() {
  const classes = useLoad(() => trackingService.list("classes"));
  const locations = useLoad(() => trackingService.list("locations"));
  const tags = useLoad(() => trackingService.tags());
  const [editing, setEditing] = useState<Editing>(null);

  if (classes.loading || locations.loading || tags.loading) {
    return <Loading />;
  }

  function afterSave() {
    setEditing(null);
    classes.reload();
    locations.reload();
    tags.reload();
  }

  function close() {
    setEditing(null);
  }

  return (
    <div>
      <PageHeader
        title="Classes, locations and tags"
        subtitle="Extra ways to slice your income and expenses. Once you add one, its field appears on invoices, expenses, bills and journal entries."
      />
      <ErrorMessage message={classes.error || locations.error || tags.error} />
      <div className="grid gap-6 lg:grid-cols-3">
        <NamedListCard
          kind="classes"
          title="Classes"
          help="e.g. departments or product lines."
          items={classes.data || []}
          onEdit={(record) => setEditing({ kind: "classes", record: record })}
        />
        <NamedListCard
          kind="locations"
          title="Locations"
          help="e.g. stores, offices or regions."
          items={locations.data || []}
          onEdit={(record) => setEditing({ kind: "locations", record: record })}
        />
        <Card
          title="Tags"
          action={
            <Button variant="ghost" onClick={() => setEditing({ kind: "tags", record: null })}>
              <Plus size={16} /> Add
            </Button>
          }
        >
          <p className="mb-3 text-sm text-gray-600">Free labels; a transaction can have several.</p>
          <DataTable
            rows={tags.data || []}
            rowKey={(row) => row.id}
            emptyText="No tags yet."
            onRowClick={(row) => setEditing({ kind: "tags", record: row })}
            columns={[
              { header: "Tag", render: (row) => row.name },
              { header: "Group", render: (row) => row.group_name },
            ]}
          />
        </Card>
      </div>
      <Modal title={editing ? (editing.kind === "tags" ? "Tag" : editing.kind === "classes" ? "Class" : "Location") : ""} open={editing !== null} onClose={close}>
        {editing && editing.kind === "tags" && <TagForm initial={editing.record} onSaved={afterSave} onCancel={close} />}
        {editing && editing.kind !== "tags" && (
          <NamedItemForm
            kind={editing.kind}
            initial={editing.record}
            items={(editing.kind === "classes" ? classes.data : locations.data) || []}
            onSaved={afterSave}
            onCancel={close}
          />
        )}
      </Modal>
    </div>
  );
}
