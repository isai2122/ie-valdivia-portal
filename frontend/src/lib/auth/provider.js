/**
 * Abstracción de AuthProvider en el frontend.
 * - Mismo patrón que el backend: interfaz + implementación local + stub de Firebase.
 * - Selector por REACT_APP_AUTH_PROVIDER (default "local").
 * - Para swap a Firebase en el futuro: setear REACT_APP_AUTH_PROVIDER=firebase,
 *   agregar REACT_APP_FIREBASE_* y reemplazar FirebaseAuthProvider.
 */
import { api, TOKEN_KEY, formatApiError } from "../api";

class AuthProvider {
  // eslint-disable-next-line no-unused-vars
  async login(email, password) { throw new Error("not implemented"); }
  async fetchMe() { throw new Error("not implemented"); }
  async logout() { throw new Error("not implemented"); }
  getToken() { return localStorage.getItem(TOKEN_KEY); }
}

export class LocalAuthProvider extends AuthProvider {
  async login(email, password) {
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      return { user: data.user };
    } catch (e) {
      throw new Error(formatApiError(e?.response?.data?.detail) || "Login failed");
    }
  }

  async fetchMe() {
    if (!localStorage.getItem(TOKEN_KEY)) return null;
    try {
      const { data } = await api.get("/auth/me");
      return data;
    } catch {
      return null;
    }
  }

  async logout() {
    try { await api.post("/auth/logout"); } catch { /* best-effort */ }
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class FirebaseAuthProvider extends AuthProvider {
  // Stub. Implementación futura con firebase/auth.
  // Vars esperadas: REACT_APP_FIREBASE_API_KEY, REACT_APP_FIREBASE_AUTH_DOMAIN,
  // REACT_APP_FIREBASE_PROJECT_ID, etc.
  async login() { throw new Error("FirebaseAuthProvider not configured yet"); }
  async fetchMe() { throw new Error("FirebaseAuthProvider not configured yet"); }
  async logout() { throw new Error("FirebaseAuthProvider not configured yet"); }
}

export function getAuthProvider() {
  const which = (process.env.REACT_APP_AUTH_PROVIDER || "local").toLowerCase();
  if (which === "firebase") return new FirebaseAuthProvider();
  return new LocalAuthProvider();
}
