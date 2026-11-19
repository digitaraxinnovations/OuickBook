import { RecurringScheduleInput } from "@/types/inputs";
import { RecurringSchedule, RunDueResult } from "@/types/models";
import { ResourceService } from "./resource.service";

export class RecurringService extends ResourceService<RecurringSchedule, RecurringScheduleInput> {
  runDue(): Promise<RunDueResult> {
    return this.api.post<RunDueResult>(this.path + "/run-due");
  }
}
