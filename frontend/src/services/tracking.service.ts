import { ApiClient } from "@/lib/api-client";
import { BudgetInput, NamedListInput, ProjectInput, TagInput } from "@/types/inputs";
import { Budget, BudgetSummary, BudgetVsActual, NamedListItem, Project, ProjectSummary, Tag } from "@/types/models";

/** Classes, locations, tags, projects and budgets. */
export class TrackingService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- classes and locations ("classes" or "locations") -----

  list(kind: "classes" | "locations"): Promise<NamedListItem[]> {
    return this.api.get<NamedListItem[]>("/" + kind);
  }

  save(kind: "classes" | "locations", input: NamedListInput, id?: number): Promise<NamedListItem> {
    if (id) {
      return this.api.put<NamedListItem>("/" + kind + "/" + id, input);
    }
    return this.api.post<NamedListItem>("/" + kind, input);
  }

  // ----- tags -----

  tags(): Promise<Tag[]> {
    return this.api.get<Tag[]>("/tags");
  }

  saveTag(input: TagInput, id?: number): Promise<Tag> {
    if (id) {
      return this.api.put<Tag>("/tags/" + id, input);
    }
    return this.api.post<Tag>("/tags", input);
  }

  // ----- projects -----

  projects(activeOnly = false): Promise<Project[]> {
    return this.api.get<Project[]>("/projects", { active_only: activeOnly });
  }

  saveProject(input: ProjectInput, id?: number): Promise<Project> {
    if (id) {
      return this.api.put<Project>("/projects/" + id, input);
    }
    return this.api.post<Project>("/projects", input);
  }

  projectSummary(id: number): Promise<ProjectSummary> {
    return this.api.get<ProjectSummary>("/projects/" + id + "/summary");
  }

  // ----- budgets -----

  budgets(): Promise<BudgetSummary[]> {
    return this.api.get<BudgetSummary[]>("/budgets");
  }

  budget(id: number): Promise<Budget> {
    return this.api.get<Budget>("/budgets/" + id);
  }

  saveBudget(input: BudgetInput, id?: number): Promise<Budget> {
    if (id) {
      return this.api.put<Budget>("/budgets/" + id, input);
    }
    return this.api.post<Budget>("/budgets", input);
  }

  deleteBudget(id: number): Promise<void> {
    return this.api.delete<void>("/budgets/" + id);
  }

  budgetVsActual(id: number, firstMonth: number, lastMonth: number): Promise<BudgetVsActual> {
    return this.api.get<BudgetVsActual>("/budgets/" + id + "/vs-actual", { first_month: firstMonth, last_month: lastMonth });
  }
}
