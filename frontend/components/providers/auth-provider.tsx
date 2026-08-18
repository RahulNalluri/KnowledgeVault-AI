"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  clearClientCredentials,
  onSessionInvalidated,
  refreshAccessToken,
} from "@/lib/api/client";
import * as authService from "@/services/auth";
import type { UserProfile } from "@/types/api";

type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: UserProfile | null;
  login: (input: authService.LoginInput) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: UserProfile) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [user, setUserState] = useState<UserProfile | null>(null);

  const invalidateSession = useCallback(() => {
    clearClientCredentials();
    setUserState(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    let active = true;
    onSessionInvalidated(invalidateSession);

    void (async () => {
      try {
        await refreshAccessToken();
        const currentUser = await authService.getCurrentUser();
        if (active) {
          setUserState(currentUser);
          setStatus("authenticated");
        }
      } catch {
        if (active) invalidateSession();
      }
    })();

    return () => {
      active = false;
      onSessionInvalidated(null);
    };
  }, [invalidateSession]);

  const login = useCallback(async (input: authService.LoginInput) => {
    await authService.login(input);
    const currentUser = await authService.getCurrentUser();
    setUserState(currentUser);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      invalidateSession();
      router.replace("/login");
    }
  }, [invalidateSession, router]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, setUser: setUserState }),
    [login, logout, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
