import { ApiClient } from "@/lib/api-client";
import {
  EmployeeInput,
  LiabilityPaymentInput,
  PaycheckInput,
  PayItemInput,
  PayrollRunInput,
  PayScheduleInput,
  TimeEntryInput,
} from "@/types/inputs";
import {
  Employee,
  LiabilityBalance,
  LiabilityPayment,
  PayItem,
  PayrollRun,
  PayrollRunSummary,
  PaySchedule,
  TimeEntry,
} from "@/types/models";

/** Employees, pay schedules, pay items, payroll runs, liabilities and time. */
export class PayrollService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- setup -----

  schedules(): Promise<PaySchedule[]> {
    return this.api.get<PaySchedule[]>("/pay-schedules");
  }

  saveSchedule(input: PayScheduleInput, id?: number): Promise<PaySchedule> {
    if (id) {
      return this.api.put<PaySchedule>("/pay-schedules/" + id, input);
    }
    return this.api.post<PaySchedule>("/pay-schedules", input);
  }

  payItems(): Promise<PayItem[]> {
    return this.api.get<PayItem[]>("/pay-items");
  }

  savePayItem(input: PayItemInput, id?: number): Promise<PayItem> {
    if (id) {
      return this.api.put<PayItem>("/pay-items/" + id, input);
    }
    return this.api.post<PayItem>("/pay-items", input);
  }

  employees(activeOnly = false): Promise<Employee[]> {
    return this.api.get<Employee[]>("/employees", { active_only: activeOnly });
  }

  saveEmployee(input: EmployeeInput, id?: number): Promise<Employee> {
    if (id) {
      return this.api.put<Employee>("/employees/" + id, input);
    }
    return this.api.post<Employee>("/employees", input);
  }

  // ----- payroll runs -----

  runs(): Promise<PayrollRunSummary[]> {
    return this.api.get<PayrollRunSummary[]>("/payroll-runs");
  }

  run(id: number): Promise<PayrollRun> {
    return this.api.get<PayrollRun>("/payroll-runs/" + id);
  }

  createRun(input: PayrollRunInput): Promise<PayrollRun> {
    return this.api.post<PayrollRun>("/payroll-runs", input);
  }

  updatePaycheck(runId: number, paycheckId: number, input: PaycheckInput): Promise<PayrollRun> {
    return this.api.put<PayrollRun>("/payroll-runs/" + runId + "/paychecks/" + paycheckId, input);
  }

  removePaycheck(runId: number, paycheckId: number): Promise<PayrollRun> {
    return this.api.delete<PayrollRun>("/payroll-runs/" + runId + "/paychecks/" + paycheckId);
  }

  approve(runId: number): Promise<PayrollRun> {
    return this.api.post<PayrollRun>("/payroll-runs/" + runId + "/approve");
  }

  voidRun(runId: number): Promise<PayrollRun> {
    return this.api.post<PayrollRun>("/payroll-runs/" + runId + "/void");
  }

  deleteRun(runId: number): Promise<void> {
    return this.api.delete<void>("/payroll-runs/" + runId);
  }

  payStub(runId: number, paycheckId: number): Promise<Blob> {
    return this.api.getBlob("/payroll-runs/" + runId + "/paychecks/" + paycheckId + "/stub");
  }

  // ----- liabilities -----

  liabilities(): Promise<LiabilityBalance[]> {
    return this.api.get<LiabilityBalance[]>("/payroll-liabilities");
  }

  liabilityPayments(): Promise<LiabilityPayment[]> {
    return this.api.get<LiabilityPayment[]>("/payroll-liabilities/payments");
  }

  payLiability(input: LiabilityPaymentInput): Promise<LiabilityPayment> {
    return this.api.post<LiabilityPayment>("/payroll-liabilities/payments", input);
  }

  voidLiabilityPayment(id: number): Promise<LiabilityPayment> {
    return this.api.post<LiabilityPayment>("/payroll-liabilities/payments/" + id + "/void");
  }

  // ----- time -----

  timeEntries(query: { start_date?: string; end_date?: string; employee_id?: number; customer_id?: number; unbilled_only?: boolean }): Promise<TimeEntry[]> {
    return this.api.get<TimeEntry[]>("/time-entries", query);
  }

  saveTimeEntry(input: TimeEntryInput, id?: number): Promise<TimeEntry> {
    if (id) {
      return this.api.put<TimeEntry>("/time-entries/" + id, input);
    }
    return this.api.post<TimeEntry>("/time-entries", input);
  }

  deleteTimeEntry(id: number): Promise<void> {
    return this.api.delete<void>("/time-entries/" + id);
  }
}
