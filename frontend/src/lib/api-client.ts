/**
 * The only place that talks to the backend over HTTP.
 * It adds the login token and turns error responses into ApiError.
 */
import { TokenStorage } from "./token-storage";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | boolean | null | undefined>;

export class ApiClient {
  private baseUrl: string;
  private tokenStorage: TokenStorage;

  constructor(baseUrl: string, tokenStorage: TokenStorage) {
    this.baseUrl = baseUrl;
    this.tokenStorage = tokenStorage;
  }

  get<T>(path: string, query?: QueryParams): Promise<T> {
    return this.request<T>("GET", path + this.buildQuery(query));
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("PUT", path, body);
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = this.tokenStorage.get();
    if (token) {
      headers["Authorization"] = "Bearer " + token;
    }

    let response: Response;
    try {
      response = await fetch(this.baseUrl + path, {
        method: method,
        headers: headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError("Cannot reach the server. Is the backend running?", 0);
    }

    let data: unknown = null;
    const text = await response.text();
    if (text) {
      data = JSON.parse(text);
    }

    if (!response.ok) {
      throw new ApiError(this.readErrorMessage(data), response.status);
    }
    return data as T;
  }

  /** FastAPI sends either {detail: "message"} or {detail: [{msg, loc}, ...]} */
  private readErrorMessage(data: unknown): string {
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: string; loc?: string[] };
        const field = first.loc ? first.loc[first.loc.length - 1] : "";
        return field ? field + ": " + first.msg : first.msg || "Invalid data.";
      }
    }
    return "Something went wrong. Please try again.";
  }

  private buildQuery(query?: QueryParams): string {
    if (!query) {
      return "";
    }
    const params = new URLSearchParams();
    for (const key of Object.keys(query)) {
      const value = query[key];
      if (value !== null && value !== undefined && value !== "") {
        params.append(key, String(value));
      }
    }
    const text = params.toString();
    return text ? "?" + text : "";
  }
}
