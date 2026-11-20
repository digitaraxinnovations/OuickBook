"use client";

import { Mail, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ScheduleDialog } from "@/components/reports/ScheduleDialog";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { dateRangeOptions } from "@/lib/date-ranges";
import { formatDate } from "@/lib/format";
import { reportService } from "@/services";
import { ReportInfo, SavedReport } from "@/types/models";

/** Address of a saved report: its key plus its period and options in the query string. */
function savedReportHref(saved: SavedReport): string {
  const query = new URLSearchParams();
  if (saved.date_range === "custom") {
    if (saved.start_date) {
      query.set("start_date", saved.start_date);
    }
    if (saved.end_date) {
      query.set("end_date", saved.end_date);
    }
  } else {
    query.set("range", saved.date_range);
  }
  for (const [name, value] of Object.entries(saved.options)) {
    if (value !== null && value !== undefined && value !== "") {
      query.set(name, String(value));
    }
  }
  return "/reports/" + saved.report_key + "?" + query.toString();
}

function groupReports(reports: ReportInfo[]): [string, ReportInfo[]][] {
  const groups: [string, ReportInfo[]][] = [];
  for (const report of reports) {
    let group = groups.find((item) => item[0] === report.group);
    if (!group) {
      group = [report.group, []];
      groups.push(group);
    }
    group[1].push(report);
  }
  return groups;
}

export default function ReportsPage() {
  const reports = useLoad(() => reportService.listReports());
  const saved = useLoad(() => reportService.savedReports());
  const schedules = useLoad(() => reportService.schedules());
  const [search, setSearch] = useState("");
  const [scheduling, setScheduling] = useState<SavedReport | null>(null);

  const titles: Record<string, string> = {};
  for (const report of reports.data || []) {
    titles[report.key] = report.title;
  }
  const rangeLabels: Record<string, string> = {};
  for (const option of dateRangeOptions) {
    rangeLabels[option.value] = option.label;
  }

  const term = search.trim().toLowerCase();
  const matching = (reports.data || []).filter(
    (report) => !term || report.title.toLowerCase().includes(term) || report.description.toLowerCase().includes(term),
  );

  async function deleteSaved(item: SavedReport) {
    if (window.confirm('Delete the custom report "' + item.name + '"?')) {
      await reportService.deleteSavedReport(item.id);
      saved.reload();
      schedules.reload();
    }
  }

  function scheduleOf(item: SavedReport) {
    return (schedules.data || []).find((schedule) => schedule.saved_report_id === item.id) || null;
  }

  return (
    <div>
      <PageHeader title="Reports" subtitle="See how your business is doing." />
      <ErrorMessage message={reports.error || saved.error} />
      <div className="relative mb-6 max-w-md">
        <Search size={16} className="absolute top-3 left-3 text-gray-400" />
        <TextInput className="pl-9!" placeholder="Find a report by name" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {(saved.data || []).length > 0 && !term && (
        <Card title="My custom reports" className="mb-6">
          <div className="divide-y divide-gray-100">
            {(saved.data || []).map((item) => {
              const schedule = scheduleOf(item);
              return (
                <div key={item.id} className="flex flex-wrap items-center gap-3 py-2">
                  <Link href={savedReportHref(item)} className="font-medium text-brand-700 hover:underline">
                    {item.name}
                  </Link>
                  <span className="text-sm text-gray-500">
                    {titles[item.report_key]} · {rangeLabels[item.date_range]}
                    {item.options.basis === "cash" ? " · Cash basis" : ""}
                  </span>
                  <span className="ml-auto text-sm text-gray-500">
                    {schedule && schedule.is_active ? "Emailed " + schedule.frequency.toLowerCase() + ", next " + formatDate(schedule.next_send_date) : ""}
                  </span>
                  <button onClick={() => setScheduling(item)} className="text-gray-500 hover:text-brand-700" aria-label="Email on a schedule" title="Email on a schedule">
                    <Mail size={16} />
                  </button>
                  <button onClick={() => deleteSaved(item)} className="text-gray-400 hover:text-red-600" aria-label="Delete custom report">
                    <Trash2 size={16} />
                  </button>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {reports.loading ? (
        <Loading />
      ) : (
        groupReports(matching).map(([group, items]) => (
          <div key={group} className="mb-6">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">{group}</h2>
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {items.map((report) => (
                <Link key={report.key} href={"/reports/" + report.key} className="rounded-md border border-gray-200 bg-white px-4 py-3 hover:border-brand-500">
                  <div className="font-medium text-gray-900">{report.title}</div>
                  <div className="text-xs text-gray-500">{report.description}</div>
                </Link>
              ))}
            </div>
          </div>
        ))
      )}
      {!term && (
        <p className="text-sm text-gray-500">
          Looking for who changed what? See the{" "}
          <Link href="/settings/audit-log" className="text-brand-700 hover:underline">
            audit log
          </Link>
          .
        </p>
      )}
      {scheduling && (
        <ScheduleDialog
          saved={scheduling}
          schedule={scheduleOf(scheduling)}
          onClose={() => setScheduling(null)}
          onSaved={() => {
            setScheduling(null);
            schedules.reload();
          }}
        />
      )}
    </div>
  );
}
