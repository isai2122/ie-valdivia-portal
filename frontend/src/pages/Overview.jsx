/**
 * Overview.jsx — Dashboard principal MetanoSRGAN Elite v5.0
 * Integra datos reales via tRPC (409 eventos Sentinel-5P, Magdalena Medio)
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis,
} from "recharts";
import {
  Activity, AlertTriangle, Cloud, Database, Gauge,
  MapPin, RefreshCw, Satellite, Shield, TrendingDown, TrendingUp,
} from "lucide-react";

import { trpc } from "@/lib/trpc";
import { useQuery } from "@/hooks/useTRPC";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { KpiCard } from "@/components/ui-extra/KpiCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ─── Helpers de formato ───────────────────────────────────────────────────────
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString("es-CO"));
const fmtPpb = (n) => (n == null ? "—" : `${Number(n).toFixed(0)} ppb`);
const fmtPct = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n}%`);

// ─── Colores por categoría ────────────────────────────────────────────────────
const CAT_COLOR = {
  "ALERTA CRÍTICA": "#ef4444",
  "ALERTA PREVENTIVA": "#f59e0b",
  "MONITOREO RUTINARIO": "#38bdf8",
};

// ─── Componente: Badge de categoría ──────────────────────────────────────────
function CatBadge({ cat }) {
  const color = CAT_COLOR[cat] || "#64748b";
  const label =
    cat === "ALERTA CRÍTICA" ? "Crítica" :
    cat === "ALERTA PREVENTIVA" ? "Preventiva" : "Rutinario";
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
      style={{ background: `${color}22`, color }}
    >
      {label}
    </span>
  );
}

// ─── Componente: Drive Sync Badge ─────────────────────────────────────────────
function DriveSyncBadge({ data }) {
  if (!data) return null;
  return (
    <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1 text-[11px] text-emerald-400">
      <Cloud className="h-3 w-3" />
      <span>Drive: {data.events_loaded} eventos reales · {data.source_file}</span>
    </div>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────
export default function Overview() {
  // Queries tRPC
  const { data: stats, loading: statsLoading } = useQuery(
    () => trpc.stats.overview(),
    [],
    { refetchInterval: 60_000 }
  );

  const { data: timeseries, loading: tsLoading } = useQuery(
    () => trpc.detections.timeseries({ days: 30 }),
    []
  );

  const { data: byStation, loading: stLoading } = useQuery(
    () => trpc.detections.byStation(),
    []
  );

  const { data: recentAlerts, loading: alertsLoading } = useQuery(
    () => trpc.alerts.recent({ limit: 6 }),
    [],
    { refetchInterval: 30_000 }
  );

  const { data: driveStatus } = useQuery(
    () => trpc.drive.syncStatus(),
    []
  );

  // ─── Datos derivados ─────────────────────────────────────────────────────
  const severityData = useMemo(() => {
    if (!stats) return [];
    return [
      { name: "Críticas",   value: stats.critical_alerts,   fill: "#ef4444" },
      { name: "Preventivas",value: stats.preventive_alerts, fill: "#f59e0b" },
      { name: "Rutinario",  value: stats.routine_monitoring,fill: "#38bdf8" },
    ];
  }, [stats]);

  const stationChartData = useMemo(() => {
    if (!byStation) return [];
    return byStation.map((s) => ({
      name: s.station,
      total: s.total,
      preventive: s.preventive,
      routine: s.routine,
      avg_ppb: s.avg_ppb,
    }));
  }, [byStation]);

  const ppbStatus = useMemo(() => {
    if (!stats) return null;
    const avg = stats.avg_ppb;
    if (avg >= 2200) return { label: "CRÍTICO", color: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/20" };
    if (avg >= 2000) return { label: "ALERTA", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" };
    return { label: "NORMAL", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" };
  }, [stats]);

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="overview-page">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          kicker="Dashboard · v5.0"
          title="Estado operacional"
          subtitle="Monitoreo de metano en tiempo real — Magdalena Medio, Colombia. Datos: Sentinel-5P TROPOMI."
        />
        <DriveSyncBadge data={driveStatus} />
      </div>

      {/* ── KPIs ── */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {statsLoading || !stats ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl bg-slate-900/60" />
          ))
        ) : (
          <>
            <KpiCard
              title="Detecciones totales"
              value={fmt(stats.total_detections)}
              hint="Fuente: Sentinel-5P TROPOMI"
              delta={fmtPct(stats.trend_7d_pct)}
              trend={stats.trend_7d_pct > 0 ? "up" : stats.trend_7d_pct < 0 ? "down" : "neutral"}
              icon={Satellite}
              tone="emerald"
            />
            <KpiCard
              title="Alertas preventivas"
              value={fmt(stats.preventive_alerts)}
              hint={`${stats.critical_alerts} críticas detectadas`}
              delta={stats.critical_alerts > 0 ? `${stats.critical_alerts} críticas` : "Sin críticas"}
              trend={stats.critical_alerts > 0 ? "up" : "down"}
              icon={AlertTriangle}
              tone={stats.critical_alerts > 0 ? "rose" : "sky"}
            />
            <KpiCard
              title="Estaciones activas"
              value={fmt(stats.active_stations)}
              hint="Vasconia · Mariquita · Barrancabermeja · Malena · Miraflores"
              icon={Shield}
              tone="sky"
            />
            <KpiCard
              title="PPB promedio"
              value={fmtPpb(stats.avg_ppb)}
              hint={`Máx: ${fmtPpb(stats.max_ppb)} · Umbral: 2000 ppb`}
              delta={ppbStatus?.label}
              trend={stats.avg_ppb >= 2000 ? "up" : "down"}
              icon={Gauge}
              tone={stats.avg_ppb >= 2200 ? "rose" : stats.avg_ppb >= 2000 ? "amber" : "emerald"}
            />
          </>
        )}
      </div>

      {/* ── PPB Status Banner ── */}
      {stats && ppbStatus && (
        <div className={`mt-4 flex items-center gap-3 rounded-xl border px-4 py-3 ${ppbStatus.bg}`}>
          {stats.avg_ppb >= 2000
            ? <TrendingUp className={`h-4 w-4 ${ppbStatus.color}`} />
            : <TrendingDown className={`h-4 w-4 ${ppbStatus.color}`} />
          }
          <span className={`text-sm font-medium ${ppbStatus.color}`}>
            Estado metano: {ppbStatus.label}
          </span>
          <span className="text-xs text-slate-400">
            Concentración promedio {fmtPpb(stats.avg_ppb)} — máxima registrada {fmtPpb(stats.max_ppb)}
          </span>
          <span className="ml-auto text-[11px] text-slate-500">
            Fuente: {stats.data_source}
          </span>
        </div>
      )}

      {/* ── Charts Row 1 ── */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {/* Serie temporal */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
                Últimos 30 días · Sentinel-5P
              </div>
              <h3 className="mt-1 text-sm font-medium text-slate-200">Detecciones por día</h3>
            </div>
            <Activity className="h-4 w-4 text-slate-500" />
          </div>
          <div className="h-56">
            {tsLoading || !timeseries ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <AreaChart data={timeseries}>
                  <defs>
                    <linearGradient id="grad-em" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#475569"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(d) => d.slice(5)}
                  />
                  <YAxis stroke="#475569" tick={{ fontSize: 10 }} allowDecimals={false} />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "#94a3b8" }}
                    itemStyle={{ color: "#e2e8f0" }}
                    formatter={(v) => [v, "Detecciones"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#10b981"
                    strokeWidth={2}
                    fill="url(#grad-em)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* Distribución por categoría */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
              Distribución
            </div>
            <h3 className="mt-1 text-sm font-medium text-slate-200">Por categoría de alerta</h3>
          </div>
          <div className="h-56">
            {statsLoading || !stats ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <BarChart data={severityData} layout="vertical" margin={{ left: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis type="number" stroke="#475569" tick={{ fontSize: 10 }} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" stroke="#475569" tick={{ fontSize: 10 }} width={72} />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    cursor={{ fill: "rgba(30,41,59,0.4)" }}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                    {severityData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* ── Charts Row 2: Estaciones ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Bar chart por estación */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
                Por estación · Datos reales
              </div>
              <h3 className="mt-1 text-sm font-medium text-slate-200">Detecciones por activo</h3>
            </div>
            <Database className="h-4 w-4 text-slate-500" />
          </div>
          <div className="h-56">
            {stLoading || !byStation ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <BarChart data={stationChartData} margin={{ bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="name" stroke="#475569" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#475569" tick={{ fontSize: 10 }} allowDecimals={false} />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    cursor={{ fill: "rgba(30,41,59,0.15)" }}
                  />
                  <Bar dataKey="preventive" name="Preventivas" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="routine" name="Rutinario" stackId="a" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* PPB promedio por estación */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-200">PPB promedio por estación</h3>
            <Gauge className="h-4 w-4 text-slate-500" />
          </div>
          {stLoading || !byStation ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-8 bg-slate-900/80" />
              ))}
            </div>
          ) : (
            <ul className="space-y-2">
              {byStation.map((s) => {
                const pct = Math.min(100, ((s.avg_ppb - 2000) / 400) * 100);
                const color = s.avg_ppb >= 2200 ? "#ef4444" : s.avg_ppb >= 2100 ? "#f59e0b" : "#10b981";
                return (
                  <li key={s.station}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-slate-300">{s.station}</span>
                      <span className="font-mono" style={{ color }}>{fmtPpb(s.avg_ppb)}</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${Math.max(5, pct)}%`, background: color }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      {/* ── Bottom: Alertas recientes + Drive status ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Alertas recientes */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-200">Alertas de mayor prioridad</h3>
            <Link to="/alerts" className="text-xs text-emerald-400 hover:underline">
              Ver todas →
            </Link>
          </div>
          {alertsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 bg-slate-900/80" />
              ))}
            </div>
          ) : !recentAlerts?.length ? (
            <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-sm text-slate-500">
              Sin alertas recientes.
            </div>
          ) : (
            <ul className="divide-y divide-slate-800/60">
              {recentAlerts.map((a) => (
                <li key={a.id_evento} className="py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <CatBadge cat={a.categoria_alerta} />
                      <div className="min-w-0">
                        <div className="truncate text-sm text-slate-200">
                          {a.activo_cercano} · {fmtPpb(a.intensidad_ppb)}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {a.fecha_deteccion?.slice(0, 10)} · Dist: {a.distancia_km} km · Viento: {a.viento_dominante_velocidad} m/s {a.viento_dominante_direccion}°
                        </div>
                      </div>
                    </div>
                    <span className="shrink-0 font-mono text-xs text-slate-400">
                      Score: {a.score_prioridad}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Drive Sync Status */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-3 flex items-center gap-2">
            <Cloud className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-medium text-slate-200">Google Drive · Sync</h3>
          </div>
          {!driveStatus ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-6 bg-slate-900/80" />
              ))}
            </div>
          ) : (
            <dl className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Estado</dt>
                <dd>
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[10px]">
                    {driveStatus.connected ? "Conectado" : "Desconectado"}
                  </Badge>
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Eventos cargados</dt>
                <dd className="font-mono text-slate-200">{fmt(driveStatus.events_loaded)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Última sincronización</dt>
                <dd className="text-slate-300">{driveStatus.last_sync?.slice(0, 10)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Archivo fuente</dt>
                <dd className="max-w-[140px] truncate text-right text-slate-300">
                  {driveStatus.source_file}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Calidad datos</dt>
                <dd>
                  <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-400 text-[10px]">
                    {driveStatus.data_freshness === "real" ? "Datos reales" : "Simulado"}
                  </Badge>
                </dd>
              </div>
              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                <RefreshCw className="h-3 w-3" />
                Sincronización cada {driveStatus.sync_interval_min} min
              </div>
            </dl>
          )}

          {/* Modelo IA */}
          <div className="mt-4 border-t border-slate-800 pt-4">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Satellite className="h-3.5 w-3.5 text-emerald-400" />
              <span>Motor IA: MetanoSRGAN Elite v2.1</span>
            </div>
            <div className="mt-1 text-[11px] text-slate-500">
              PSNR 32.19 dB · RRDB + Swin Transformer
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[11px]">
              <MapPin className="h-3 w-3 text-slate-500" />
              <span className="text-slate-500">Magdalena Medio · 5 activos monitoreados</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
