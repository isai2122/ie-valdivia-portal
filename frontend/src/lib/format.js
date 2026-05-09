/** Utilidades de formato sin libs pesadas. */
export function formatNumber(n, opts = {}) {
  if (n == null || isNaN(n)) return "—";
  return new Intl.NumberFormat("es-CO", opts).format(n);
}

export function formatInt(n) {
  return formatNumber(n, { maximumFractionDigits: 0 });
}

export function formatPpb(n) {
  if (n == null) return "—";
  return `${formatNumber(n, { maximumFractionDigits: 0 })} ppb`;
}

export function formatArea(km2) {
  if (km2 == null) return "—";
  return `${formatNumber(km2, { maximumFractionDigits: 2 })} km²`;
}

export function formatPct(p) {
  if (p == null) return "—";
  return `${formatNumber(p * 100, { maximumFractionDigits: 0 })}%`;
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("es-CO", {
    year: "numeric", month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "2-digit" });
}

export function timeAgo(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const s = Math.max(1, Math.floor((Date.now() - d.getTime()) / 1000));
  if (s < 60) return `hace ${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `hace ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h} h`;
  const dd = Math.floor(h / 24);
  return `hace ${dd} d`;
}

/** Municipio más cercano dado un array [{name,lat,lng}] */
export function nearestPlace(lat, lng, places = []) {
  if (!places?.length) return "—";
  let best = places[0], bestD = Infinity;
  for (const p of places) {
    const d = Math.hypot(p.lat - lat, p.lng - lng);
    if (d < bestD) { bestD = d; best = p; }
  }
  return best.name;
}
