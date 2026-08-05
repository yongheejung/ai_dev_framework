"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { getToken } from "@/shared/auth/token-store";

interface AuthContextValue {
  hasToken: boolean;
  setHasToken: (value: boolean) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthContextProvider({ children }: { children: ReactNode }) {
  const [hasToken, setHasToken] = useState(false);

  // 최초 렌더(서버/클라이언트 첫 페인트)는 토큰 유무를 모른다고 가정하고, 마운트 후 localStorage를 읽는다.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHasToken(getToken() !== null);
  }, []);

  return <AuthContext.Provider value={{ hasToken, setHasToken }}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthContextProvider");
  }
  return ctx;
}
