"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useFormState } from "@/hooks/useFormState";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate, formatLabel, formatMoney, todayString, toNumber } from "@/lib/format";
import { mileageService } from "@/services";
import { TripInput } from "@/types/inputs";
import { Trip, TripPurpose } from "@/types/models";

function tripToInput(trip: Trip | null): TripInput {
  return {
    trip_date: trip?.trip_date || todayString(),
    vehicle: trip?.vehicle || "",
    start_location: trip?.start_location || "",
    end_location: trip?.end_location || "",
    miles: trip?.miles || "",
    purpose: trip?.purpose || "BUSINESS",
    notes: trip?.notes || "",
  };
}

function TripForm({ initial, onSave, onCancel }: { initial: Trip | null; onSave: (input: TripInput) => Promise<void>; onCancel: () => void }) {
  const form = useFormState<TripInput>(tripToInput(initial));
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave(form.values);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Date" required>
          <TextInput type="date" required value={form.values.trip_date} onChange={(e) => form.setField("trip_date", e.target.value)} />
        </Field>
        <Field label="Miles" required>
          <TextInput type="number" step="0.1" min="0.1" required value={form.values.miles} onChange={(e) => form.setField("miles", e.target.value)} />
        </Field>
        <Field label="From">
          <TextInput value={form.values.start_location} onChange={(e) => form.setField("start_location", e.target.value)} />
        </Field>
        <Field label="To">
          <TextInput value={form.values.end_location} onChange={(e) => form.setField("end_location", e.target.value)} />
        </Field>
        <Field label="Vehicle">
          <TextInput value={form.values.vehicle} onChange={(e) => form.setField("vehicle", e.target.value)} />
        </Field>
        <Field label="Purpose">
          <Select
            value={form.values.purpose}
            onChange={(e) => form.setField("purpose", e.target.value as TripPurpose)}
            options={[
              { value: "BUSINESS", label: "Business" },
              { value: "PERSONAL", label: "Personal" },
            ]}
          />
        </Field>
      </div>
      <Field label="Notes">
        <TextInput value={form.values.notes} onChange={(e) => form.setField("notes", e.target.value)} />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save trip</Button>
      </div>
    </form>
  );
}

export default function MileagePage() {
  const { company } = useAuth();
  const [year, setYear] = useState(new Date().getFullYear());
  const trips = useLoad(() => mileageService.trips(year), [year]);
  const summary = useLoad(() => mileageService.summary(year), [year]);
  const [editing, setEditing] = useState<Trip | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [rate, setRate] = useState("");
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setFormOpen(true);
    }
  }, [openFromMenu]);

  useEffect(() => {
    if (summary.data) {
      setRate(summary.data.rate);
    }
  }, [summary.data]);

  function reloadAll() {
    trips.reload();
    summary.reload();
  }

  async function save(input: TripInput) {
    if (editing) {
      await mileageService.updateTrip(editing.id, input);
    } else {
      await mileageService.createTrip(input);
    }
    setFormOpen(false);
    reloadAll();
  }

  async function remove(trip: Trip) {
    if (window.confirm("Delete this trip?")) {
      await mileageService.deleteTrip(trip.id);
      reloadAll();
    }
  }

  async function saveRate() {
    await mileageService.setRate(rate);
    summary.reload();
  }

  const years = [];
  for (let value = new Date().getFullYear(); value >= new Date().getFullYear() - 5; value--) {
    years.push({ value: value, label: String(value) });
  }

  return (
    <div>
      <PageHeader
        title="Mileage"
        subtitle="Log business trips. Business miles x the mileage rate = your deduction."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} /> Add trip
          </Button>
        }
      />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Business miles</div>
          <div className="mt-1 text-2xl font-semibold">{toNumber(summary.data?.business_miles).toLocaleString()}</div>
        </Card>
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Personal miles</div>
          <div className="mt-1 text-2xl font-semibold">{toNumber(summary.data?.personal_miles).toLocaleString()}</div>
        </Card>
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Rate per mile</div>
          <div className="mt-1 flex items-center gap-2">
            <TextInput type="number" step="0.001" min="0" value={rate} onChange={(e) => setRate(e.target.value)} className="w-24!" />
            <Button variant="ghost" onClick={saveRate}>
              Save
            </Button>
          </div>
        </Card>
        <Card>
          <div className="text-xs font-semibold uppercase text-gray-500">Deduction ({year})</div>
          <div className="mt-1 text-2xl font-semibold text-brand-700">{formatMoney(summary.data?.deduction, company?.currency)}</div>
        </Card>
      </div>
      <div className="mb-4 w-40">
        <Select value={year} onChange={(e) => setYear(Number(e.target.value))} options={years} />
      </div>
      <ErrorMessage message={trips.error} />
      {trips.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={trips.data || []}
          rowKey={(row) => row.id}
          onRowClick={(row) => {
            setEditing(row);
            setFormOpen(true);
          }}
          emptyText="No trips in this year."
          columns={[
            { header: "Date", render: (row) => formatDate(row.trip_date) },
            { header: "Purpose", render: (row) => formatLabel(row.purpose) },
            { header: "From / to", render: (row) => [row.start_location, row.end_location].filter(Boolean).join(" → ") || "-" },
            { header: "Vehicle", render: (row) => row.vehicle },
            { header: "Miles", align: "right", render: (row) => toNumber(row.miles) },
            {
              header: "",
              align: "right",
              render: (row) => (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    remove(row);
                  }}
                  className="text-gray-400 hover:text-red-600"
                  aria-label="Delete trip"
                >
                  <Trash2 size={16} />
                </button>
              ),
            },
          ]}
        />
      )}
      <Modal title={editing ? "Edit trip" : "Add trip"} open={formOpen} onClose={() => setFormOpen(false)}>
        <TripForm key={editing ? editing.id : "new"} initial={editing} onSave={save} onCancel={() => setFormOpen(false)} />
      </Modal>
    </div>
  );
}
