import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { AlertTriangle, MapPin } from "lucide-react";

import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const MAPBOX_TOKEN = process.env.REACT_APP_MAPBOX_TOKEN;

export default function MapPage() {
  const mapDivRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const [stations, setStations] = useState([]);
  const [error, setError] = useState(null);
  const [params] = useSearchParams();
  const focusStation = params.get("station");

  // Cargar estaciones
  useEffect(() => {
    const ctrl = new AbortController();
    api.get("/stations", { signal: ctrl.signal })
      .then((r) => setStations(r.data || []))
      .catch((e) => setError(e?.message || "No se pudieron cargar las estaciones"));
    return () => ctrl.abort();
  }, []);

  // Inicializar mapa
  useEffect(() => {
    if (!MAPBOX_TOKEN || !mapDivRef.current || mapRef.current) return;
    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
      container: mapDivRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [-74.2, 6.5], zoom: 7,
    });
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: "metric" }), "bottom-left");
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; markersRef.current = []; };
  }, []);

  // Pines
  useEffect(() => {
    const map = mapRef.current;
    if (!map || stations.length === 0) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    stations.forEach((s) => {
      const el = document.createElement("div");
      el.setAttribute("data-testid", `station-marker-${s.id}`);
      el.className = "msrgan-pin";
      el.innerHTML = `<span class="msrgan-pin-dot"></span><span class="msrgan-pin-ring"></span>`;
      const popup = new mapboxgl.Popup({ offset: 24, closeButton: true, className: "msrgan-mapbox-popup" })
        .setHTML(`
          <div class="msrgan-popup" data-testid="station-popup-${s.id}">
            <div class="msrgan-popup-kicker">${s.type.replace("_"," ")}</div>
            <div class="msrgan-popup-title">${s.name}</div>
            <div class="msrgan-popup-sub">${s.municipality}, ${s.department}</div>
            <div class="msrgan-popup-meta">
              <span>Operador · <b>${s.operator}</b></span>
              <span>Capacidad · <b>${s.capacity_mmscfd} mmscfd</b> (${s.installation_year})</span>
              <span>Riesgo · <b>${s.risk_level}</b></span>
              <span>Lat ${s.lat.toFixed(4)} · Lng ${s.lng.toFixed(4)}</span>
            </div>
          </div>`);
      const m = new mapboxgl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([s.lng, s.lat]).setPopup(popup).addTo(map);
      markersRef.current.push({ id: s.id, marker: m, popup });
    });
  }, [stations]);

  // Focus desde query param ?station=id
  useEffect(() => {
    if (!focusStation) return;
    const map = mapRef.current;
    const s = stations.find((x) => x.id === focusStation);
    if (!map || !s) return;
    map.flyTo({ center: [s.lng, s.lat], zoom: 11, speed: 1.2 });
    const entry = markersRef.current.find((x) => x.id === focusStation);
    setTimeout(() => entry?.marker?.togglePopup(), 700);
  }, [focusStation, stations]);

  return (
    <div className="grid h-[calc(100vh-3.5rem)] grid-cols-1 xl:grid-cols-[1fr_320px]" data-testid="map-page">
      {/* Mapa */}
      <div className="relative">
        {!MAPBOX_TOKEN && (
          <div className="absolute inset-0 z-10 grid place-items-center bg-slate-950" data-testid="map-no-token">
            <div className="max-w-md rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 text-amber-200">
              <div className="mb-2 flex items-center gap-2 font-semibold">
                <AlertTriangle className="h-4 w-4" /> Mapbox token faltante
              </div>
              <p className="text-sm">Configura <code className="rounded bg-slate-900 px-1">REACT_APP_MAPBOX_TOKEN</code> en <code className="rounded bg-slate-900 px-1">frontend/.env</code>.</p>
            </div>
          </div>
        )}
        <div ref={mapDivRef} className="h-full w-full" data-testid="map-container" />
        <div className="pointer-events-none absolute left-4 top-4 z-[1] rounded-lg border border-slate-700/60 bg-slate-950/70 px-3 py-2 text-xs backdrop-blur">
          <div className="flex items-center gap-2 text-emerald-300">
            <MapPin className="h-3.5 w-3.5" />
            <span data-testid="map-status-stations">{stations.length} estaciones cargadas</span>
          </div>
          <div className="mt-1 font-mono text-[10px] text-slate-400">center -74.2, 6.5 · zoom 7</div>
        </div>
        {error && (
          <div className="absolute bottom-4 left-1/2 z-[1] -translate-x-1/2 rounded-md border border-rose-500/40 bg-rose-900/50 px-3 py-2 text-xs text-rose-200" data-testid="map-error">
            {error}
          </div>
        )}
      </div>

      {/* Panel derecho: filtros + leyenda placeholder */}
      <aside className="hidden border-l border-slate-800/80 bg-slate-950/70 p-5 xl:block" data-testid="map-sidepanel">
        <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">Panel</div>
        <h3 className="mt-1 text-sm font-semibold text-slate-200">Capas y filtros</h3>

        <Card className="mt-4 border-slate-800/80 bg-slate-900/50 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">Filtros</div>
          <p className="mt-2 text-xs text-slate-400">
            Severidad, rango temporal, confianza mínima y capas de infraestructura
            estarán disponibles en <b className="text-slate-300">Fase 3</b>.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="outline" className="border-slate-700 text-slate-400">severidad</Badge>
            <Badge variant="outline" className="border-slate-700 text-slate-400">fechas</Badge>
            <Badge variant="outline" className="border-slate-700 text-slate-400">confianza</Badge>
          </div>
        </Card>

        <Card className="mt-4 border-slate-800/80 bg-slate-900/50 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">Leyenda</div>
          <ul className="mt-3 space-y-2 text-xs">
            <li className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_0_3px_rgba(16,185,129,.2)]" />
              Estación de compresión
            </li>
            <li className="flex items-center gap-2 opacity-60">
              <span className="h-2.5 w-2.5 rounded-full bg-sky-400" /> Pozos (Fase 3)
            </li>
            <li className="flex items-center gap-2 opacity-60">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" /> Detecciones (Fase 3)
            </li>
            <li className="flex items-center gap-2 opacity-60">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-400" /> Plumas críticas (Fase 3)
            </li>
          </ul>
        </Card>
      </aside>
    </div>
  );
}
