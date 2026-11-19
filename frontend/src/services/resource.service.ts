import { ApiClient } from "@/lib/api-client";

/**
 * Standard list / get / create / update calls for one API resource.
 * Services with extra actions (like invoices) extend this class.
 */
export class ResourceService<TRead, TInput> {
  protected api: ApiClient;
  protected path: string;

  constructor(api: ApiClient, path: string) {
    this.api = api;
    this.path = path;
  }

  list(query?: Record<string, string | number | boolean | null | undefined>): Promise<TRead[]> {
    return this.api.get<TRead[]>(this.path, query);
  }

  get(id: number): Promise<TRead> {
    return this.api.get<TRead>(this.path + "/" + id);
  }

  create(input: TInput): Promise<TRead> {
    return this.api.post<TRead>(this.path, input);
  }

  update(id: number, input: TInput): Promise<TRead> {
    return this.api.put<TRead>(this.path + "/" + id, input);
  }
}
