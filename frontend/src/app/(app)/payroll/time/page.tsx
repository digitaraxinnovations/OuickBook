"use client";

import { ChevronLeft, ChevronRight, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, todayString, toNumber } from "@/lib/format";
import { customerService, payrollService, productService, trackingService, vendorService } from "@/services";
import { TimeEntry } from "@/types/models";

// ---------- dates (local, no time zones) ----------

function parseDay(text: string): Date {
  const [year, month, day] = text.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function dayText(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return day.getFullYear() + "-" + month + "-" + date;
}

function addDays(text: string, days: number): string {
  const day = parseDay(text);
  day.setDate(day.getDate() + days);
  return dayText(day);
}

/** The Monday of the week that contains this day. */
function mondayOf(text: string): string {
  const day = parseDay(text);
  const offset = (day.getDay() + 6) % 7;
  return addDays(text, -offset);
}

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// ---------- one row of the timesheet ----------

interface SheetRow {
  customerId: string;
  projectId: string;
  productId: string;
  description: string;
  billable: boolean;
  /** Price per hour charged to the customer. */
  billRate: string;
  hours: string[];
}

function emptyRow(): SheetRow {
  return { customerId: "", projectId: "", productId: "", description: "", billable: false, billRate: "", hours: ["", "", "", "", "", "", ""] };
}

export default function TimePage() {
  const [weekStart, setWeekStart] = useState(mondayOf(todayString()));
  const [worker, setWorker] = useState("");
  const [rows, setRows] = useState<SheetRow[]>([emptyRow()]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const employees = useLoad(() => payrollService.employees(true));
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const products = useLoad(() => productService.list({ active_only: true }));
  const projects = useLoad(() => trackingService.projects(true));
  const weekEnd = addDays(weekStart, 6);
  const entries = useLoad(() => payrollService.timeEntries({ start_date: weekStart, end_date: weekEnd }), [weekStart]);

  if (employees.loading || vendors.loading || customers.loading || products.loading) {
    return <Loading />;
  }

  // "E12" = employee 12, "V3" = vendor (contractor) 3.
  const workerOptions = [
    ...(employees.data || []).map((employee) => ({ value: "E" + employee.id, label: employee.display_name })),
    ...(vendors.data || []).map((vendor) => ({ value: "V" + vendor.id, label: vendor.display_name + " (contractor)" })),
  ];
  const workerNames: Record<string, string> = {};
  for (const option of workerOptions) {
    workerNames[option.value] = option.label;
  }
  const customerNames: Record<number, string> = {};
  for (const customer of customers.data || []) {
    customerNames[customer.id] = customer.display_name;
  }
  const services = (products.data || []).filter((product) => product.product_type === "SERVICE");
  const allProjects = projects.data || [];

  function projectOptionsFor(customerId: string) {
    return allProjects.filter((project) => String(project.customer_id) === customerId).map((project) => ({ value: project.id, label: project.name }));
  }

  function updateRow(index: number, changes: Partial<SheetRow>) {
    setRows(rows.map((row, i) => (i === index ? { ...row, ...changes } : row)));
  }

  /** Picking a service fills in its price as the bill rate. */
  function chooseService(index: number, productId: string) {
    const service = services.find((product) => product.id === Number(productId));
    updateRow(index, { productId: productId, billRate: service ? service.sales_price : rows[index].billRate });
  }

  function setHours(rowIndex: number, dayIndex: number, value: string) {
    const hours = rows[rowIndex].hours.map((old, i) => (i === dayIndex ? value : old));
    updateRow(rowIndex, { hours: hours });
  }

  function rowTotal(row: SheetRow): number {
    let total = 0;
    for (const value of row.hours) {
      total += toNumber(value);
    }
    return total;
  }

  async function saveSheet() {
    if (!worker) {
      setError("Choose who did the work.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    let saved = 0;
    try {
      for (const row of rows) {
        for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
          if (toNumber(row.hours[dayIndex]) <= 0) {
            continue;
          }
          await payrollService.saveTimeEntry({
            employee_id: worker.startsWith("E") ? Number(worker.slice(1)) : null,
            vendor_id: worker.startsWith("V") ? Number(worker.slice(1)) : null,
            work_date: addDays(weekStart, dayIndex),
            hours: row.hours[dayIndex],
            customer_id: row.customerId ? Number(row.customerId) : null,
            project_id: row.projectId ? Number(row.projectId) : null,
            product_id: row.productId ? Number(row.productId) : null,
            description: row.description,
            billable: row.billable,
            bill_rate: row.billable && row.billRate ? row.billRate : null,
          });
          saved += 1;
        }
      }
      setRows([emptyRow()]);
      setMessage(saved + " time entries saved.");
      entries.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the timesheet.");
      entries.reload();
    }
    setSaving(false);
  }

  async function deleteEntry(entry: TimeEntry) {
    try {
      await payrollService.deleteTimeEntry(entry.id);
      entries.reload();
    } catch (problem) {
      window.alert(problem instanceof Error ? problem.message : "Could not delete.");
    }
  }

  function entryWorker(entry: TimeEntry): string {
    if (entry.employee_id) {
      return workerNames["E" + entry.employee_id] || "";
    }
    return workerNames["V" + entry.vendor_id] || "";
  }

  let weekHours = 0;
  for (const entry of entries.data || []) {
    weekHours += toNumber(entry.hours);
  }

  return (
    <div>
      <PageHeader title="Time" subtitle="Hours worked. Billable hours can be added to the customer's invoice; employee hours fill in their paychecks." />
      <ErrorMessage message={error} />
      {message && <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</div>}

      <Card title="Weekly timesheet" className="mb-6">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Select className="w-64!" value={worker} onChange={(e) => setWorker(e.target.value)} placeholder="Who did the work?" options={workerOptions} />
          <div className="flex items-center gap-1">
            <Button variant="ghost" onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Previous week">
              <ChevronLeft size={16} />
            </Button>
            <span className="text-sm font-medium">
              {formatDate(weekStart)} - {formatDate(weekEnd)}
            </span>
            <Button variant="ghost" onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Next week">
              <ChevronRight size={16} />
            </Button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1060px] text-sm">
            <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="w-44 py-2">Customer</th>
                {allProjects.length > 0 && <th className="w-36 py-2">Project</th>}
                <th className="w-40 py-2">Service</th>
                <th className="py-2">Description</th>
                <th className="w-14 py-2 text-center">Bill</th>
                <th className="w-20 py-2">Rate</th>
                {DAY_NAMES.map((name, index) => (
                  <th key={name} className="w-16 py-2 text-center">
                    {name} {parseDay(addDays(weekStart, index)).getDate()}
                  </th>
                ))}
                <th className="w-14 py-2 text-right">Total</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b border-gray-100">
                  <td className="py-2 pr-2">
                    <Select
                      value={row.customerId}
                      onChange={(e) => updateRow(rowIndex, { customerId: e.target.value, projectId: "" })}
                      placeholder="-"
                      options={(customers.data || []).map((customer) => ({ value: customer.id, label: customer.display_name }))}
                    />
                  </td>
                  {allProjects.length > 0 && (
                    <td className="py-2 pr-2">
                      <Select
                        value={row.projectId}
                        onChange={(e) => updateRow(rowIndex, { projectId: e.target.value })}
                        placeholder="-"
                        disabled={!row.customerId}
                        options={projectOptionsFor(row.customerId)}
                      />
                    </td>
                  )}
                  <td className="py-2 pr-2">
                    <Select
                      value={row.productId}
                      onChange={(e) => chooseService(rowIndex, e.target.value)}
                      placeholder="-"
                      options={services.map((product) => ({ value: product.id, label: product.name }))}
                    />
                  </td>
                  <td className="py-2 pr-2">
                    <TextInput value={row.description} onChange={(e) => updateRow(rowIndex, { description: e.target.value })} />
                  </td>
                  <td className="py-2 text-center">
                    <input
                      type="checkbox"
                      aria-label="Billable"
                      checked={row.billable}
                      disabled={!row.customerId}
                      onChange={(e) => updateRow(rowIndex, { billable: e.target.checked })}
                    />
                  </td>
                  <td className="py-2 pr-1">
                    <TextInput
                      className="px-1!"
                      type="number"
                      step="0.01"
                      min="0"
                      value={row.billRate}
                      disabled={!row.billable}
                      onChange={(e) => updateRow(rowIndex, { billRate: e.target.value })}
                      aria-label="Bill rate"
                    />
                  </td>
                  {row.hours.map((value, dayIndex) => (
                    <td key={dayIndex} className="px-1 py-2">
                      <TextInput
                        className="px-1! text-center"
                        type="number"
                        step="0.25"
                        min="0"
                        max="24"
                        value={value}
                        onChange={(e) => setHours(rowIndex, dayIndex, e.target.value)}
                        aria-label={DAY_NAMES[dayIndex] + " hours"}
                      />
                    </td>
                  ))}
                  <td className="py-2 text-right font-medium">{rowTotal(row)}</td>
                  <td className="py-2 pl-2">
                    {rows.length > 1 && (
                      <button type="button" onClick={() => setRows(rows.filter((_, i) => i !== rowIndex))} className="text-gray-400 hover:text-red-600" aria-label="Remove row">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex justify-between">
          <Button variant="ghost" onClick={() => setRows([...rows, emptyRow()])}>
            <Plus size={16} /> Add row
          </Button>
          <Button onClick={saveSheet} disabled={saving}>
            {saving ? "Saving..." : "Save timesheet"}
          </Button>
        </div>
      </Card>

      <Card title={"Time this week: " + weekHours + " hours"}>
        <ErrorMessage message={entries.error} />
        <DataTable
          rows={entries.data || []}
          rowKey={(row) => row.id}
          emptyText="No time entered for this week."
          columns={[
            { header: "Date", render: (row) => formatDate(row.work_date) },
            { header: "Who", render: (row) => entryWorker(row) },
            { header: "Customer", render: (row) => (row.customer_id ? customerNames[row.customer_id] : "") },
            { header: "Description", render: (row) => row.description },
            { header: "Hours", align: "right", render: (row) => toNumber(row.hours) },
            {
              header: "Billing",
              render: (row) => (row.invoice_id ? "Invoiced" : row.billable ? "Billable" : ""),
            },
            {
              header: "Delete",
              align: "right",
              render: (row) =>
                row.invoice_id ? null : (
                  <button onClick={() => deleteEntry(row)} className="text-gray-400 hover:text-red-600" aria-label="Delete entry">
                    <Trash2 size={16} />
                  </button>
                ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
