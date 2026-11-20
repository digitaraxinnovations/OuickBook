import { ApiClient } from "@/lib/api-client";
import { TokenStorage } from "@/lib/token-storage";
import { LoginInput, SignupInput } from "@/types/inputs";
import { Company, CompanyMembership, User, UserRole } from "@/types/models";

interface TokenResponse {
  access_token: string;
}

export interface CurrentSession {
  user: User;
  company: Company;
  role: UserRole;
  companies: CompanyMembership[];
}

export class AuthService {
  private api: ApiClient;
  private tokenStorage: TokenStorage;

  constructor(api: ApiClient, tokenStorage: TokenStorage) {
    this.api = api;
    this.tokenStorage = tokenStorage;
  }

  async login(input: LoginInput): Promise<void> {
    const result = await this.api.post<TokenResponse>("/auth/login", input);
    this.tokenStorage.save(result.access_token);
  }

  async signup(input: SignupInput): Promise<void> {
    const result = await this.api.post<TokenResponse>("/auth/signup", input);
    this.tokenStorage.save(result.access_token);
  }

  /** Join a company from an invitation link (creating the account if needed) and sign in. */
  async acceptInvitation(token: string, fullName: string, password: string): Promise<void> {
    const result = await this.api.post<TokenResponse>("/auth/invitations/" + token + "/accept", { full_name: fullName || null, password: password });
    this.tokenStorage.save(result.access_token);
  }

  logout(): void {
    this.tokenStorage.clear();
  }

  hasToken(): boolean {
    return this.tokenStorage.get() !== null;
  }

  getCurrentSession(): Promise<CurrentSession> {
    return this.api.get<CurrentSession>("/auth/me");
  }
}
