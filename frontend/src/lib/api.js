/**
 * Cliente axios centralizado.
 * - Usa REACT_APP_BACKEND_URL (+ /api) en todas las llamadas.
 * - Adjunta Bearer desde localStorage (key msrgan_token).
 * - En 401, borra el token y dispara un evento "msrgan:unauthorized".
 */
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const BASE = `${BACKEND_URL}/api`;
export const TOKEN_KEY = "msrgan_token";

export const api = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new CustomEvent("msrgan:unauthorized"));
    }
    return Promise.reject(err);
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Algo salió mal. Intenta de nuevo.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e?.msg ? e.msg : JSON.stringify(e))).join(" ");
  if (detail?.msg) return detail.msg;
  return String(detail);
}
