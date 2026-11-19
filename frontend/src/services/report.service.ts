import { ApiClient } from "@/lib/api-client";
import { DashboardSummary, ReportInfo, ReportResult } from "@/types/models";

export class ReportService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  listReports(): Promise<ReportInfo[]> {
    return this.api.get<ReportInfo[]>("/reports");
  }

  runReport(key: string, startDate: string, endDate: string): Promise<ReportResult> {
    return this.api.get<ReportResult>("/reports/" + key, { start_date: startDate, end_date: endDate });
  }

  getDashboard(): Promise<DashboardSummary> {
    return this.api.get<DashboardSummary>("/dashboard");
  }
}
