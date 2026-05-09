/**
 * Cliente tRPC para MetanoSRGAN Elite v5.0
 * Wrapper sobre axios que expone procedimientos tipados.
 * Compatible con el router /api/trpc/* del backend FastAPI.
 */
import { api } from "./api";

// ─── Helper base ─────────────────────────────────────────────────────────────
async function query(procedure, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
  ).toString();
  const url = `/trpc/${procedure}${qs ? `?${qs}` : ""}`;
  const res = await api.get(url);
  return res.data?.result ?? res.data;
}

async function mutation(procedure, body = {}) {
  const res = await api.post(`/trpc/${procedure}`, body);
  return res.data?.result ?? res.data;
}

// ─── tRPC Client ─────────────────────────────────────────────────────────────
export const trpc = {
  /**
   * stats.overview — KPIs principales del dashboard
   * @returns {{ total_detections, critical_alerts, preventive_alerts, avg_ppb, max_ppb, trend_7d_pct, ... }}
   */
  stats: {
    overview: () => query("stats.overview"),
  },

  /**
   * detections.* — Gestión de detecciones
   */
  detections: {
    list: (params = {}) => query("detections.list", params),
    byStation: () => query("detections.byStation"),
    timeseries: (params = {}) => query("detections.timeseries", params),
  },

  /**
   * stations.* — Estaciones de compresión
   */
  stations: {
    list: () => query("stations.list"),
  },

  /**
   * alerts.* — Sistema de alertas
   */
  alerts: {
    recent: (params = {}) => query("alerts.recent", params),
    heatmap: () => query("alerts.heatmap"),
  },

  /**
   * model.* — Estado del modelo IA
   */
  model: {
    status: () => query("model.status"),
  },

  /**
   * pipeline.* — Control del pipeline
   */
  pipeline: {
    run: (body = {}) => mutation("pipeline.run", body),
  },

  /**
   * drive.* — Integración con Google Drive
   */
  drive: {
    syncStatus: () => query("drive.syncStatus"),
  },
};

export default trpc;
