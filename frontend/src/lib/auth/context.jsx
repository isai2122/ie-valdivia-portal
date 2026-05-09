import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAuthProvider } from "./provider";

const AuthCtx = createContext(null);

export function AuthProviderRoot({ children }) {
  const provider = useMemo(() => getAuthProvider(), []);
  const [user, setUser] = useState(null);         // null = not authed, objeto = authed
  const [loading, setLoading] = useState(true);   // true hasta resolver me()

  const refresh = useCallback(async () => {
    const me = await provider.fetchMe();
    setUser(me);
    setLoading(false);
  }, [provider]);

  useEffect(() => {
    refresh();
    const onUnauth = () => setUser(null);
    window.addEventListener("msrgan:unauthorized", onUnauth);
    return () => window.removeEventListener("msrgan:unauthorized", onUnauth);
  }, [refresh]);

  const login = useCallback(async (email, password) => {
    const { user: u } = await provider.login(email, password);
    setUser(u);
    return u;
  }, [provider]);

  const logout = useCallback(async () => {
    await provider.logout();
    setUser(null);
  }, [provider]);

  const value = useMemo(() => ({ user, loading, login, logout, refresh }), [
    user, loading, login, logout, refresh,
  ]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProviderRoot");
  return ctx;
}

export function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400" data-testid="auth-loading">
        Cargando sesión…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/403" replace />;
  return children;
}
