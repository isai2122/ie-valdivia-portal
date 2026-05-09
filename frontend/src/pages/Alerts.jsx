/**
 * Alerts.jsx — Panel de alertas MetanoSRGAN Elite v5.0
 * Datos reales de 409 eventos Sentinel-5P via tRPC
 */
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Bell, Cloud, Filter, MapPin, RefreshCw, Wind } from "lucide-react";

import { trpc } from "@/lib/trpc";
import { useQuery } from "@/hooks/useTRPC";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STATIONS = ["Todas", "Vasconia", "Mariquita", "Barrancabermeja", "Malena", "Miraflores"];
const CATEGORIES = ["Todas", "ALERTA PREVENTIVA", "MONITOREO RUTINARIO"];

const fmtPpb = (n) => `${Number(n).toFixed(0)} ppb`;
const fmt = (n) => Number(n).toLocaleString("es-CO");

function CatBadge({ cat }) {
  const map = {
    "ALERTA CRÍTICA":    { bg: "#ef444422", color: "#ef4444", label: "Crítica" },
    "ALERTA PREVENTIVA": { bg: "#f59e0b22", color: "#f59e0b", label: "Preventiva" },
    "MONITOREO RUTINARIO": { bg: "#38bdf822", color: "#38bdf8", label: "Rutinario" },
  };
  const s = map[cat] || { bg: "#64748b22", color: "#64748b", label: cat };
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
      style={{ background: s.bg, color: s.color }}
    >
      {s.label}
    </span>
  );
}

function AlertDetail({ alert, onClose }) {
  if (!alert) return null;
  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-sm border-l border-slate-800 bg-slate-950 p-6 shadow-2xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Detalle de alerta</h2>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0 text-slate-400">✕</Button>
      </div>

      <div className="space-y-4 text-xs">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <CatBadge cat={alert.categoria_alerta} />
          <div className="mt-2 text-lg font-mono font-bold text-emerald-400">{fmtPpb(alert.intensidad_ppb)}</div>
          <div className="text-slate-400">Score de prioridad: {alert.score_prioridad}</div>
        </div>

        <dl className="space-y-2">
          <div className="flex justify-between">
            <dt className="text-slate-400">Activo cercano</dt>
            <dd className="font-medium text-slate-200">{alert.activo_cercano}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-400">Distancia</dt>
            <dd className="text-slate-300">{alert.distancia_km} km</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-400">Fecha detección</dt>
            <dd className="text-slate-300">{alert.fecha_deteccion?.slice(0, 19).replace("T", " ")}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-400">Fuente</dt>
            <dd className="text-slate-300">{alert.fuente}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-400">Persistencia</dt>
            <dd className="text-slate-300">{alert.persistencia_dias} día(s)</dd>
          </div>
        </dl>

        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-slate-400">
            <Wind className="h-3 w-3" /> Condiciones de viento
          </div>
          <div className="text-slate-200">
            {alert.viento_dominante_velocidad} m/s · {alert.viento_dominante_direccion}° (dirección dominante)
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-slate-400">
            <MapPin className="h-3 w-3" /> Coordenadas
          </div>
          <div className="font-mono text-slate-300">
            {alert.latitud?.toFixed(6)}, {alert.longitud?.toFixed(6)}
          </div>
        </div>

        <div className="text-[10px] text-slate-500">ID: {alert.id_evento}</div>
      </div>
    </div>
  );
}

export default function AlertsPage() {
  const [selectedStation, setSelectedStation] = useState("Todas");
  const [selectedCat, setSelectedCat] = useState("Todas");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedAlert, setSelectedAlert] = useState(null);

  // ── tRPC Queries ──────────────────────────────────────────────────────────
  const { data: alertsData, loading, refetch } = useQuery(
    () => trpc.detections.list({
      page,
      limit: 20,
      station: selectedStation !== "Todas" ? selectedStation : undefined,
      category: selectedCat !== "Todas" ? selectedCat : undefined,
    }),
    [page, selectedStation, selectedCat],
    { refetchInterval: 60_000 }
  );

  const { data: stats } = useQuery(() => trpc.stats.overview(), []);

  const handleRefresh = useCallback(() => {
    refetch();
    toast.success("Datos actualizados");
  }, [refetch]);

  // Filtro de búsqueda local
  const filteredItems = (alertsData?.items || []).filter((a) =>
    !search ||
    a.activo_cercano?.toLowerCase().includes(search.toLowerCase()) ||
    a.id_evento?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="alerts-page">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          kicker="Alertas · Datos reales"
          title="Panel de alertas"
          subtitle="Detecciones de metano en tiempo real — Sentinel-5P TROPOMI, Magdalena Medio."
        />
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          className="border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800"
        >
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Actualizar
        </Button>
      </div>

      {/* ── KPI Badges ── */}
      {stats && (
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge variant="outline" className="border-amber-500/30 bg-amber-500/5 text-amber-400 text-[11px]">
            <AlertTriangle className="mr-1 h-3 w-3" />
            {fmt(stats.preventive_alerts)} preventivas
          </Badge>
          <Badge variant="outline" className="border-sky-500/30 bg-sky-500/5 text-sky-400 text-[11px]">
            <Bell className="mr-1 h-3 w-3" />
            {fmt(stats.routine_monitoring)} rutinario
          </Badge>
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/5 text-emerald-400 text-[11px]">
            <Cloud className="mr-1 h-3 w-3" />
            {fmt(stats.total_detections)} total · Sentinel-5P
          </Badge>
        </div>
      )}

      {/* ── Filtros ── */}
      <Card className="mb-4 border-slate-800/80 bg-slate-900/60 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter className="h-3.5 w-3.5" /> Filtros:
          </div>
          <Input
            placeholder="Buscar por activo o ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 w-52 border-slate-700 bg-slate-950 text-xs text-slate-200 placeholder:text-slate-500"
          />
          <Select value={selectedStation} onValueChange={(v) => { setSelectedStation(v); setPage(1); }}>
            <SelectTrigger className="h-8 w-44 border-slate-700 bg-slate-950 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATIONS.map((s) => (
                <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedCat} onValueChange={(v) => { setSelectedCat(v); setPage(1); }}>
            <SelectTrigger className="h-8 w-48 border-slate-700 bg-slate-950 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((c) => (
                <SelectItem key={c} value={c} className="text-xs">
                  {c === "Todas" ? "Todas las categorías" :
                   c === "ALERTA PREVENTIVA" ? "Preventivas" : "Rutinario"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(selectedStation !== "Todas" || selectedCat !== "Todas" || search) && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs text-slate-400"
              onClick={() => { setSelectedStation("Todas"); setSelectedCat("Todas"); setSearch(""); setPage(1); }}
            >
              Limpiar filtros
            </Button>
          )}
        </div>
      </Card>

      {/* ── Tabla de alertas ── */}
      <Card className="border-slate-800/80 bg-slate-900/60">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-left">
                <th className="px-4 py-3 font-medium text-slate-400">Categoría</th>
                <th className="px-4 py-3 font-medium text-slate-400">Activo</th>
                <th className="px-4 py-3 font-medium text-slate-400">PPB</th>
                <th className="px-4 py-3 font-medium text-slate-400">Score</th>
                <th className="px-4 py-3 font-medium text-slate-400">Distancia</th>
                <th className="px-4 py-3 font-medium text-slate-400">Viento</th>
                <th className="px-4 py-3 font-medium text-slate-400">Fecha</th>
                <th className="px-4 py-3 font-medium text-slate-400">Fuente</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={8} className="px-4 py-2">
                      <Skeleton className="h-6 bg-slate-900/80" />
                    </td>
                  </tr>
                ))
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                    No se encontraron alertas con los filtros actuales.
                  </td>
                </tr>
              ) : (
                filteredItems.map((a) => (
                  <tr
                    key={a.id_evento}
                    className="cursor-pointer hover:bg-slate-800/30"
                    onClick={() => setSelectedAlert(a)}
                  >
                    <td className="px-4 py-2.5">
                      <CatBadge cat={a.categoria_alerta} />
                    </td>
                    <td className="px-4 py-2.5 font-medium text-slate-200">{a.activo_cercano}</td>
                    <td className="px-4 py-2.5 font-mono text-emerald-400">{fmtPpb(a.intensidad_ppb)}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-300">{a.score_prioridad}</td>
                    <td className="px-4 py-2.5 text-slate-400">{a.distancia_km} km</td>
                    <td className="px-4 py-2.5 text-slate-400">
                      {a.viento_dominante_velocidad} m/s · {a.viento_dominante_direccion}°
                    </td>
                    <td className="px-4 py-2.5 text-slate-400">{a.fecha_deteccion?.slice(0, 10)}</td>
                    <td className="px-4 py-2.5 text-slate-500">{a.fuente}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {alertsData && alertsData.pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
            <span className="text-xs text-slate-400">
              Página {alertsData.page} de {alertsData.pages} · {fmt(alertsData.total)} total
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="h-7 border-slate-700 bg-slate-900 text-xs"
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= alertsData.pages}
                onClick={() => setPage((p) => p + 1)}
                className="h-7 border-slate-700 bg-slate-900 text-xs"
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Panel lateral de detalle */}
      {selectedAlert && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40"
            onClick={() => setSelectedAlert(null)}
          />
          <AlertDetail alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
        </>
      )}
    </div>
  );
}
