"use client";

import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { useLoad } from "@/hooks/useLoad";
import { dateRangeOptions } from "@/lib/date-ranges";
import { accountService, customerService, trackingService, vendorService } from "@/services";
import { ReportInfo, ReportOptions } from "@/types/models";

const COLUMN_OPTIONS = [
  { value: "total", label: "Total only" },
  { value: "month", label: "Months" },
  { value: "quarter", label: "Quarters" },
  { value: "year", label: "Years" },
  { value: "customer", label: "Customers" },
  { value: "vendor", label: "Vendors" },
  { value: "class", label: "Classes" },
  { value: "location", label: "Locations" },
];

const COMPARE_OPTIONS = [
  { value: "previous_period", label: "Previous period" },
  { value: "previous_year", label: "Previous year" },
];

/** Loads a list only when the report has that filter (so unused lists are not fetched). */
function useOptionalList<T>(wanted: boolean, load: () => Promise<T[]>) {
  return useLoad(() => (wanted ? load() : Promise.resolve([] as T[])), [wanted]);
}

export interface DateState {
  range: string;
  startDate: string;
  endDate: string;
}

interface ReportToolbarProps {
  info: ReportInfo;
  dates: DateState;
  onDatesChange: (dates: DateState) => void;
  options: ReportOptions;
  onOptionsChange: (options: ReportOptions) => void;
  onRangeChange: (range: string) => void;
}

/** Date range and the options this report supports (basis, columns, compare, filters). */
export function ReportToolbar({ info, dates, onDatesChange, options, onOptionsChange, onRangeChange }: ReportToolbarProps) {
  const supports = (name: string) => info.options.includes(name);
  // What the report is really using: its own defaults (e.g. "by month"), then the user's choices.
  const shown: ReportOptions = { ...info.defaults, ...options };
  const customers = useOptionalList(supports("customer_id"), () => customerService.list());
  const vendors = useOptionalList(supports("vendor_id"), () => vendorService.list());
  const classes = useOptionalList(supports("class_id"), () => trackingService.list("classes"));
  const locations = useOptionalList(supports("location_id"), () => trackingService.list("locations"));
  const projects = useOptionalList(supports("project_id"), () => trackingService.projects());
  const accounts = useOptionalList(supports("account_id"), () => accountService.list());

  function setOption(name: keyof ReportOptions, value: string | number | null) {
    onOptionsChange({ ...options, [name]: value });
  }

  function numberOrNull(text: string): number | null {
    return text ? Number(text) : null;
  }

  function filter(name: keyof ReportOptions, label: string, items: { id: number; label: string }[]) {
    if (!supports(name) || items.length === 0) {
      return null;
    }
    return (
      <div className="w-48">
        <Field label={label}>
          <Select
            value={(options[name] as number | null | undefined) ?? ""}
            onChange={(e) => setOption(name, numberOrNull(e.target.value))}
            placeholder="All"
            options={items.map((item) => ({ value: item.id, label: item.label }))}
          />
        </Field>
      </div>
    );
  }

  return (
    <div className="no-print mb-6 flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="w-40">
        <Field label="Report period">
          <Select value={dates.range} onChange={(e) => onRangeChange(e.target.value)} options={dateRangeOptions} />
        </Field>
      </div>
      {info.uses_start_date && (
        <div className="w-40">
          <Field label="From">
            <TextInput type="date" value={dates.startDate} onChange={(e) => onDatesChange({ ...dates, range: "custom", startDate: e.target.value })} />
          </Field>
        </div>
      )}
      <div className="w-40">
        <Field label={info.uses_start_date ? "To" : "As of"}>
          <TextInput type="date" value={dates.endDate} onChange={(e) => onDatesChange({ ...dates, range: "custom", endDate: e.target.value })} />
        </Field>
      </div>
      {supports("basis") && (
        <div className="w-36">
          <Field label="Accounting method">
            <Select
              value={shown.basis || "accrual"}
              onChange={(e) => setOption("basis", e.target.value)}
              options={[
                { value: "accrual", label: "Accrual" },
                { value: "cash", label: "Cash" },
              ]}
            />
          </Field>
        </div>
      )}
      {supports("column_by") && (
        <div className="w-40">
          <Field label="Show columns">
            <Select value={shown.column_by || "total"} onChange={(e) => setOption("column_by", e.target.value)} options={COLUMN_OPTIONS} />
          </Field>
        </div>
      )}
      {supports("compare") && (
        <div className="w-40">
          <Field label="Compare with">
            <Select value={shown.compare || ""} onChange={(e) => setOption("compare", e.target.value || null)} placeholder="Nothing" options={COMPARE_OPTIONS} />
          </Field>
        </div>
      )}
      {filter("customer_id", "Customer", (customers.data || []).map((item) => ({ id: item.id, label: item.display_name })))}
      {filter("vendor_id", "Vendor", (vendors.data || []).map((item) => ({ id: item.id, label: item.display_name })))}
      {filter("class_id", "Class", (classes.data || []).map((item) => ({ id: item.id, label: item.name })))}
      {filter("location_id", "Location", (locations.data || []).map((item) => ({ id: item.id, label: item.name })))}
      {filter("project_id", "Project", (projects.data || []).map((item) => ({ id: item.id, label: item.name })))}
      {filter("account_id", "Account", (accounts.data || []).map((item) => ({ id: item.id, label: item.full_name })))}
    </div>
  );
}
