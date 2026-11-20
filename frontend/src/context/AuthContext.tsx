"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { authService, platformService } from "@/services";
import { LoginInput, SignupInput } from "@/types/inputs";
import { Company, CompanyMembership, User, UserRole } from "@/types/models";

interface AuthState {
  user: User | null;
  company: Company | null;
  /** The user's role in the current company. */
  role: UserRole | null;
  /** Every company the user can open. */
  companies: CompanyMembership[];
  loading: boolean;
  switchCompany: (companyId: number) => Promise<void>;
  createCompany: (name: string) => Promise<void>;
  login: (input: LoginInput) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [companies, setCompanies] = useState<CompanyMembership[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!authService.hasToken()) {
      setUser(null);
      setCompany(null);
      setLoading(false);
      return;
    }
    try {
      const session = await authService.getCurrentSession();
      setUser(session.user);
      setCompany(session.company);
      setRole(session.role);
      setCompanies(session.companies);
    } catch {
      authService.logout();
      setUser(null);
      setCompany(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function login(input: LoginInput) {
    await authService.login(input);
    await refresh();
  }

  async function signup(input: SignupInput) {
    await authService.signup(input);
    await refresh();
  }

  async function switchCompany(companyId: number) {
    await platformService.switchCompany(companyId);
    await refresh();
  }

  async function createCompany(name: string) {
    await platformService.createCompany(name);
    await refresh();
  }

  function logout() {
    authService.logout();
    setUser(null);
    setCompany(null);
  }

  return (
    <AuthContext.Provider value={{ user, company, role, companies, loading, login, signup, logout, refresh, switchCompany, createCompany }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return state;
}
