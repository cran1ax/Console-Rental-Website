import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authAPI } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ── Bootstrap: fetch user if tokens exist ───────────────── */
  useEffect(() => {
    const access = localStorage.getItem("access");
    if (!access) {
      setLoading(false);
      return;
    }
    authAPI
      .getMe()
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
      })
      .finally(() => setLoading(false));
  }, []);

  /* ── Login ───────────────────────────────────────────────── */
  const login = useCallback(async (email, password) => {
    const { data } = await authAPI.login(email, password);
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    const { data: me } = await authAPI.getMe();
    setUser(me);
    return me;
  }, []);

  /* ── Register ────────────────────────────────────────────── */
  const register = useCallback(async (payload) => {
    const { data } = await authAPI.register(payload);
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    const { data: me } = await authAPI.getMe();
    setUser(me);
    return me;
  }, []);

  /* ── Logout ──────────────────────────────────────────────── */
  const logout = useCallback(async () => {
    const refresh = localStorage.getItem("refresh");
    try {
      if (refresh) await authAPI.logout(refresh);
    } catch {
      /* swallow — token may already be blacklisted */
    }
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  }, []);

  /* ── Refresh user data ───────────────────────────────────── */
  const refreshUser = useCallback(async () => {
    try {
      const { data } = await authAPI.getMe();
      setUser(data);
    } catch {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
