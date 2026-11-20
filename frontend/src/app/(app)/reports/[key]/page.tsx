"use client";

import { Download, Printer, Save } from "lucide-react";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { DateState, ReportToolbar } from "@/components/reports/ReportToolbar";
import { ReportView } from "@/components/reports/ReportView";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { resolveDateRange } from "@/lib/date-ranges";
import { openBlobInNewTab, saveBlob } from "@/lib/files";
import { todayString } from "@/lib/format";
import { reportService } from "@/services";
import { ReportOptions } from "@/types/models";

const OPTION_NAMES = ["basis", "column_by", "compare", "class_id", "location_id", "customer_id", "vendor_id", "project_id", "account_id"];
const NUMBER_OPTIONS = ["class_id", "location_id", "customer_id", "vendor_id", "project_id", "account_id"];

/** Dates and options from the address (used by saved reports and drill-down links). */
function readAddress(): { dates: DateState; options: ReportOptions } {
  const params = new URLSearchParams(window.location.search);
  const range = params.get("range") || "this_year";
  const resolved = resolveDateRange(range);
  const dates: DateState = {
    range: params.get("start_date") || params.get("end_date") ? "custom" : range,
    startDate: params.get("start_date") || (resolved ? resolved[0] : ""),
    endDate: params.get("end_date") || (resolved ? resolved[1] : todayString()),
  };
  const options: Record<string, string | number> = {};
  for (const name of OPTION_NAMES) {
    const value = params.get(name);
    if (value) {
      options[name] = NUMBER_OPTIONS.includes(name) ? Number(value) : value;
    }
  }
  return { dates, options: options as ReportOptions };
}

export default function ReportPage() {
  const params = useParams<{ key: string }>();
  const { company } = useAuth();
  const reports = useLoad(() => reportService.listReports());
  const [ready, setReady] = useState(false);
  const [dates, setDates] = useState<DateState>({ range: "this_year", startDate: "", endDate: "" });
  const [options, setOptions] = useState<ReportOptions>({});
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const fromAddress = readAddress();
    setDates(fromAddress.dates);
    setOptions(fromAddress.options);
    setReady(true);
  }, [params.key]);

  const info = (reports.data || []).find((item) => item.key === params.key);
  const startDate = info && !info.uses_start_date ? null : dates.startDate || null;
  const report = useLoad(
    () => (ready ? reportService.runReport(params.key, startDate, dates.endDate, options) : Promise.resolve(null)),
    [params.key, ready, startDate, dates.endDate, JSON.stringify(options)],
  );

  if (reports.loading || !ready) {
    return <Loading />;
  }
  if (!info) {
    return <ErrorMessage message={reports.error || "This report does not exist."} />;
  }

  function changeRange(range: string) {
    const resolved = resolveDateRange(range);
    if (resolved) {
      setDates({ range: range, startDate: resolved[0], endDate: resolved[1] });
    } else {
      setDates({ ...dates, range: range });
    }
  }

  async function exportAs(fileFormat: string) {
    setActionError(null);
    try {
      const blob = await reportService.exportReport(params.key, fileFormat, startDate, dates.endDate, options);
      if (fileFormat === "pdf") {
        openBlobInNewTab(blob);
      } else {
        saveBlob(blob, (report.data?.title || params.key) + "." + fileFormat);
      }
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : "Could not export.");
    }
  }

  async function saveCustom(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    try {
      await reportService.saveReport({
        name: saveName,
        report_key: params.key,
        date_range: dates.range,
        start_date: dates.range === "custom" ? startDate : null,
        end_date: dates.range === "custom" ? dates.endDate : null,
        options: options,
      });
      setSaveOpen(false);
      setMessage('Saved as "' + saveName + '". Find it under Reports → My custom reports.');
    } catch (problem) {
      setActionError(problem instanceof Error ? problem.message : "Could not save.");
    }
  }

  /** Clicking an account opens its Account QuickReport for the same dates. */
  function accountLink(accountId: number): string {
    const query = new URLSearchParams({ account_id: String(accountId), end_date: dates.endDate });
    if (startDate) {
      query.set("start_date", startDate);
    }
    return "/reports/account-quickreport?" + query.toString();
  }

  return (
    <div>
      <PageHeader
        title={info.title}
        subtitle={info.description}
        actions={
          <div className="no-print flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setSaveName(info.title);
                setSaveOpen(true);
              }}
            >
              <Save size={16} /> Save as custom
            </Button>
            <Button variant="secondary" onClick={() => exportAs("pdf")}>
              <Download size={16} /> PDF
            </Button>
            <Button variant="secondary" onClick={() => exportAs("xlsx")}>
              <Download size={16} /> Excel
            </Button>
            <Button variant="secondary" onClick={() => exportAs("csv")}>
              <Download size={16} /> CSV
            </Button>
            <Button variant="secondary" onClick={() => window.print()}>
              <Printer size={16} /> Print
            </Button>
          </div>
        }
      />
      <ReportToolbar info={info} dates={dates} onDatesChange={setDates} options={options} onOptionsChange={setOptions} onRangeChange={changeRange} />
      <ErrorMessage message={report.error || actionError} />
      {message && <div className="no-print mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</div>}
      {report.loading && <Loading />}
      {!report.loading && report.data && (
        <ReportView report={report.data} companyName={company?.name || ""} currency={company?.currency} accountLink={accountLink} />
      )}
      <Modal title="Save as custom report" open={saveOpen} onClose={() => setSaveOpen(false)}>
        <form onSubmit={saveCustom} className="space-y-4">
          <Field label="Name" required>
            <TextInput required value={saveName} onChange={(e) => setSaveName(e.target.value)} />
          </Field>
          <p className="text-sm text-gray-600">
            The report&apos;s options and its period ({dates.range === "custom" ? "these exact dates" : "always relative to today"}) are saved.
          </p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setSaveOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Save</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
