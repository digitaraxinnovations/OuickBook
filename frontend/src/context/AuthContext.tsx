"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { authService } from "@/services";
import { LoginInput, SignupInput } from "@/types/inputs";
import { Company, User } from "@/types/models";

interface AuthState {
  user: User | null;
  company: Company | null;
  loading: boolean;
  login: (input: LoginInput) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
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

  function logout() {
    authService.logout();
    setUser(null);
    setCompany(null);
  }

  return (
    <AuthContext.Provider value={{ user, company, loading, login, signup, logout, refresh }}>
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
