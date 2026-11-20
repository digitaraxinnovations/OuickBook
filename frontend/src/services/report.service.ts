import { ApiClient } from "@/lib/api-client";
import { DashboardSummary, ReportInfo, ReportOptions, ReportResult, ReportSchedule, SavedReport } from "@/types/models";

/** Query string values for a report run: dates plus the options that are set. */
function reportQuery(startDate: string | null, endDate: string, options: ReportOptions): Record<string, string | number> {
  const query: Record<string, string | number> = { end_date: endDate };
  if (startDate) {
    query.start_date = startDate;
  }
  for (const [name, value] of Object.entries(options)) {
    if (value !== null && value !== undefined && value !== "") {
      query[name] = value;
    }
  }
  return query;
}

export class ReportService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  listReports(): Promise<ReportInfo[]> {
    return this.api.get<ReportInfo[]>("/reports");
  }

  runReport(key: string, startDate: string | null, endDate: string, options: ReportOptions = {}): Promise<ReportResult> {
    return this.api.get<ReportResult>("/reports/" + key, reportQuery(startDate, endDate, options));
  }

  /** The report as a "pdf", "csv" or "xlsx" file. */
  exportReport(key: string, fileFormat: string, startDate: string | null, endDate: string, options: ReportOptions = {}): Promise<Blob> {
    const query = reportQuery(startDate, endDate, options);
    query.file_format = fileFormat;
    return this.api.getBlob("/reports/" + key + "/export", query);
  }

  getDashboard(): Promise<DashboardSummary> {
    return this.api.get<DashboardSummary>("/dashboard");
  }

  // ----- saved (custom) reports -----

  savedReports(): Promise<SavedReport[]> {
    return this.api.get<SavedReport[]>("/saved-reports");
  }

  saveReport(input: Omit<SavedReport, "id">, id?: number): Promise<SavedReport> {
    if (id) {
      return this.api.put<SavedReport>("/saved-reports/" + id, input);
    }
    return this.api.post<SavedReport>("/saved-reports", input);
  }

  deleteSavedReport(id: number): Promise<void> {
    return this.api.delete<void>("/saved-reports/" + id);
  }

  // ----- scheduled emails -----

  schedules(): Promise<ReportSchedule[]> {
    return this.api.get<ReportSchedule[]>("/report-schedules");
  }

  saveSchedule(input: Omit<ReportSchedule, "id" | "last_sent_at">, id?: number): Promise<ReportSchedule> {
    if (id) {
      return this.api.put<ReportSchedule>("/report-schedules/" + id, input);
    }
    return this.api.post<ReportSchedule>("/report-schedules", input);
  }

  deleteSchedule(id: number): Promise<void> {
    return this.api.delete<void>("/report-schedules/" + id);
  }

  sendDueNow(): Promise<{ sent: number }> {
    return this.api.post<{ sent: number }>("/report-schedules/send-due");
  }
}
