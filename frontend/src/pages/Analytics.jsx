/**
 * Analytics.jsx — Análisis avanzado MetanoSRGAN Elite v5.0
 * Datos reales de 409 eventos Sentinel-5P via tRPC
 */
import { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  Legend, Line, LineChart, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip as RTooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { BarChart3, Database, Filter, TrendingUp, Wind } from "lucide-react";

import { trpc } from "@/lib/trpc";
import { useQuery } from "@/hooks/useTRPC";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const STATIONS = ["Todas", "Vasconia", "Mariquita", "Barrancabermeja", "Malena", "Miraflores"];
const DAYS_OPTIONS = [7, 14, 30, 60, 90];

const fmtPpb = (n) => `${Number(n).toFixed(0)} ppb`;
const fmt = (n) => Number(n).toLocaleString("es-CO");

export default function Analytics() {
  const [selectedStation, setSelectedStation] = useState("Todas");
  const [days, setDays] = useState(30);

  // ── tRPC Queries ──────────────────────────────────────────────────────────
  const { data: timeseries, loading: tsLoading } = useQuery(
    () => trpc.detections.timeseries({ days }),
    [days]
  );

  const { data: byStation, loading: stLoading } = useQuery(
    () => trpc.detections.byStation(),
    []
  );

  const { data: detections, loading: detLoading } = useQuery(
    () => trpc.detections.list({
      limit: 200,
      station: selectedStation !== "Todas" ? selectedStation : undefined,
    }),
    [selectedStation]
  );

  const { data: stats } = useQuery(() => trpc.stats.overview(), []);

  // ── Datos derivados ───────────────────────────────────────────────────────
  const scatterData = useMemo(() => {
    if (!detections?.items) return [];
    return detections.items.map((e) => ({
      x: e.viento_dominante_velocidad ?? 0,
      y: e.intensidad_ppb ?? 0,
      z: e.score_prioridad ?? 0,
      station: e.activo_cercano,
      cat: e.categoria_alerta,
    }));
  }, [detections]);

  const windRoseData = useMemo(() => {
    if (!detections?.items) return [];
    const bins = {};
    for (const e of detections.items) {
      const dir = e.viento_dominante_direccion ?? 0;
      const sector = Math.round(dir / 45) * 45 % 360;
      const label = `${sector}°`;
      bins[label] = (bins[label] || 0) + 1;
    }
    return Object.entries(bins)
      .map(([dir, count]) => ({ dir, count }))
      .sort((a, b) => parseInt(a.dir) - parseInt(b.dir));
  }, [detections]);

  const stationComparison = useMemo(() => {
    if (!byStation) return [];
    return byStation.map((s) => ({
      name: s.station,
      avg_ppb: s.avg_ppb,
      max_ppb: s.max_ppb,
      total: s.total,
      preventive: s.preventive,
    }));
  }, [byStation]);

  const ppbByDay = useMemo(() => {
    if (!timeseries) return [];
    return timeseries.map((t) => ({
      ...t,
      threshold: 2000,
      alert_zone: 2200,
    }));
  }, [timeseries]);

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="analytics-page">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          kicker="Análisis · Datos reales"
          title="Análisis de detecciones"
          subtitle="409 eventos Sentinel-5P — Magdalena Medio. Correlaciones, tendencias y distribuciones."
        />
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/5 text-emerald-400 text-[11px]">
            <Database className="mr-1 h-3 w-3" />
            {fmt(stats?.total_detections ?? 409)} eventos
          </Badge>
        </div>
      </div>

      {/* ── Filtros ── */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Filter className="h-3.5 w-3.5" /> Filtros:
        </div>
        <Select value={selectedStation} onValueChange={setSelectedStation}>
          <SelectTrigger className="h-8 w-44 border-slate-700 bg-slate-900/60 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATIONS.map((s) => (
              <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="h-8 w-32 border-slate-700 bg-slate-900/60 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DAYS_OPTIONS.map((d) => (
              <SelectItem key={d} value={String(d)} className="text-xs">Últimos {d}d</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ── Row 1: PPB Temporal + Comparación estaciones ── */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* PPB promedio diario */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
                Evolución temporal · {days} días
              </div>
              <h3 className="mt-1 text-sm font-medium text-slate-200">PPB promedio diario vs umbral operacional</h3>
            </div>
            <TrendingUp className="h-4 w-4 text-slate-500" />
          </div>
          <div className="h-64">
            {tsLoading ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <LineChart data={ppbByDay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#475569"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(d) => d.slice(5)}
                  />
                  <YAxis
                    stroke="#475569"
                    tick={{ fontSize: 10 }}
                    domain={[1900, "auto"]}
                  />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    formatter={(v, name) => [
                      name === "avg_ppb" ? fmtPpb(v) :
                      name === "threshold" ? "2000 ppb (umbral)" :
                      "2200 ppb (alerta)",
                      name === "avg_ppb" ? "PPB promedio" : name,
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="avg_ppb"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    name="PPB promedio"
                  />
                  <Line
                    type="monotone"
                    dataKey="threshold"
                    stroke="#f59e0b"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Umbral 2000"
                  />
                  <Line
                    type="monotone"
                    dataKey="alert_zone"
                    stroke="#ef4444"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Zona crítica 2200"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* Comparación max PPB por estación */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
              Comparativa
            </div>
            <h3 className="mt-1 text-sm font-medium text-slate-200">PPB máximo por estación</h3>
          </div>
          <div className="h-64">
            {stLoading ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <BarChart data={stationComparison} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis
                    type="number"
                    stroke="#475569"
                    tick={{ fontSize: 9 }}
                    domain={[2000, "auto"]}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#475569"
                    tick={{ fontSize: 9 }}
                    width={88}
                  />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    formatter={(v) => [fmtPpb(v), "PPB máx"]}
                  />
                  <Bar dataKey="max_ppb" radius={[0, 6, 6, 0]} name="PPB máx">
                    {stationComparison.map((s, i) => (
                      <Cell
                        key={i}
                        fill={s.max_ppb >= 2250 ? "#ef4444" : s.max_ppb >= 2150 ? "#f59e0b" : "#10b981"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* ── Row 2: Scatter PPB vs Viento + Rosa de vientos ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Scatter: PPB vs velocidad de viento */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
              Correlación
            </div>
            <h3 className="mt-1 text-sm font-medium text-slate-200">PPB vs velocidad de viento</h3>
          </div>
          <div className="h-64">
            {detLoading ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    type="number"
                    dataKey="x"
                    name="Viento (m/s)"
                    stroke="#475569"
                    tick={{ fontSize: 10 }}
                    label={{ value: "Viento (m/s)", position: "insideBottom", offset: -2, fontSize: 10, fill: "#64748b" }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name="PPB"
                    stroke="#475569"
                    tick={{ fontSize: 10 }}
                    domain={[2000, "auto"]}
                  />
                  <ZAxis type="number" dataKey="z" range={[20, 200]} />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    formatter={(v, name) => [
                      name === "Viento (m/s)" ? `${v} m/s` :
                      name === "PPB" ? fmtPpb(v) : v,
                      name,
                    ]}
                  />
                  <Scatter
                    data={scatterData}
                    fill="#10b981"
                    fillOpacity={0.6}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* Rosa de vientos (distribución por dirección) */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
                Dirección dominante
              </div>
              <h3 className="mt-1 text-sm font-medium text-slate-200">Distribución de viento por sector</h3>
            </div>
            <Wind className="h-4 w-4 text-slate-500" />
          </div>
          <div className="h-64">
            {detLoading ? (
              <Skeleton className="h-full w-full bg-slate-900/80" />
            ) : (
              <ResponsiveContainer>
                <BarChart data={windRoseData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="dir" stroke="#475569" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#475569" tick={{ fontSize: 10 }} allowDecimals={false} />
                  <RTooltip
                    contentStyle={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                    formatter={(v) => [v, "Detecciones"]}
                  />
                  <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* ── Row 3: Tabla de detecciones filtradas ── */}
      <Card className="mt-4 border-slate-800/80 bg-slate-900/60 p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
              Datos tabulares
            </div>
            <h3 className="mt-1 text-sm font-medium text-slate-200">
              Detecciones recientes
              {selectedStation !== "Todas" && ` · ${selectedStation}`}
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            {detections?.total ? `${fmt(detections.total)} total` : ""}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-left text-slate-400">
                <th className="pb-2 pr-4 font-medium">Activo</th>
                <th className="pb-2 pr-4 font-medium">Fecha</th>
                <th className="pb-2 pr-4 font-medium">PPB</th>
                <th className="pb-2 pr-4 font-medium">Score</th>
                <th className="pb-2 pr-4 font-medium">Viento</th>
                <th className="pb-2 font-medium">Categoría</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {detLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="py-2">
                      <Skeleton className="h-5 bg-slate-900/80" />
                    </td>
                  </tr>
                ))
              ) : (
                (detections?.items || []).slice(0, 12).map((e) => (
                  <tr key={e.id_evento} className="hover:bg-slate-800/20">
                    <td className="py-2 pr-4 font-medium text-slate-200">{e.activo_cercano}</td>
                    <td className="py-2 pr-4 text-slate-400">{e.fecha_deteccion?.slice(0, 10)}</td>
                    <td className="py-2 pr-4 font-mono text-emerald-400">{fmtPpb(e.intensidad_ppb)}</td>
                    <td className="py-2 pr-4 font-mono text-slate-300">{e.score_prioridad}</td>
                    <td className="py-2 pr-4 text-slate-400">
                      {e.viento_dominante_velocidad} m/s · {e.viento_dominante_direccion}°
                    </td>
                    <td className="py-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                        style={{
                          background: e.categoria_alerta === "ALERTA PREVENTIVA" ? "#f59e0b22" : "#38bdf822",
                          color: e.categoria_alerta === "ALERTA PREVENTIVA" ? "#f59e0b" : "#38bdf8",
                        }}
                      >
                        {e.categoria_alerta === "ALERTA PREVENTIVA" ? "Preventiva" : "Rutinario"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
