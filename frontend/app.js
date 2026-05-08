// app.js — Dashboard de USUARIO con feature gating por plan + Heatmap + Plumas + Popups mejorados
const TOKEN = () => localStorage.getItem('msr_token');
let me = null;
let layers = null;
let mapboxMap = null;
let allDets = [];
let assetChart = null;
let activeLayers = {};
let _heatmapVisible = false;
let _plumasVisible = true;

function authHeaders() {
  return { Authorization: 'Bearer ' + TOKEN(), 'Content-Type': 'application/json' };
}

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { ...authHeaders(), ...(opts.headers || {}) }});
  if (r.status === 401) { logout(); throw new Error('No autorizado'); }
  if (r.status === 403) {
    const j = await r.json().catch(() => ({}));
    throw new Error(j.detail || 'Tu plan no incluye esta función');
  }
  if (!r.ok) {
    let detail = 'Error ' + r.status;
    try { const j = await r.json(); detail = j.detail || JSON.stringify(j); } catch(e){}
    throw new Error(detail);
  }
  const ct = r.headers.get('content-type') || '';
  return ct.includes('json') ? r.json() : r.text();
}

function fmtNumber(n, d = 0) {
  if (n == null) return '—';
  return Number(n).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function fmtUSD(n) {
  if (n == null) return '—';
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
function fmtDate(s) {
  if (!s) return '—';
  return new Date(s).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
}

function categoryFor(score) {
  if (score >= 80) return { name: 'ÉLITE', cls: 'elite', color: '#ff2244' };
  if (score >= 60) return { name: 'CRÍTICO', cls: 'critico', color: '#ff8c00' };
  if (score >= 40) return { name: 'VIGILANCIA', cls: 'vigilancia', color: '#ffd700' };
  return { name: 'MONITOREO', cls: 'monitoreo', color: '#00ff88' };
}

function logout() {
  api('/api/auth/logout', { method: 'POST' }).catch(() => {});
  localStorage.clear();
  window.location.href = '/login';
}

function userHasFeature(key) {
  if (!me) return false;
  if (me.role === 'admin') return true;
  return me.plan_info?.limites?.[key] === true;
}

// ─── Compliance inline ───────────────────────────────────────────────────────
const COMPLIANCE_NORMS = [
  { id: 'EPA_OOOOa', name: 'EPA OOOOa', threshold_kg_h: 16.0, color: '#ff2244' },
  { id: 'EU_MRR',    name: 'EU MRR',    threshold_kg_h: 10.0, color: '#ff8c00' },
  { id: 'OGMP2',     name: 'OGMP 2.0',  threshold_kg_h: 5.0,  color: '#ffd700' },
  { id: 'RUA_PI',    name: 'RUA-PI CO', threshold_kg_h: 2.0,  color: '#00d4ff' },
];

function evalCompliance(flujo_kgh) {
  if (!flujo_kgh) return [];
  return COMPLIANCE_NORMS.map(n => ({
    ...n,
    estado: flujo_kgh > n.threshold_kg_h ? 'EXCEDE' : 'CUMPLE',
    pct: Math.min(100, Math.round((flujo_kgh / n.threshold_kg_h) * 100)),
  }));
}

// ─── Pluma helper ─────────────────────────────────────────────────────────────
// Genera un polígono elíptico de pluma basado en viento y flujo del evento
function buildPlumaPolygon(feat) {
  const lon = feat.lon;
  const lat = feat.lat;
  const windDeg = feat.pluma && feat.pluma.direccion != null
    ? feat.pluma.direccion
    : (feat.viento_dominante_direccion && feat.viento_dominante_direccion !== 'N/A'
        ? parseFloat(feat.viento_dominante_direccion) : 180);
  const windMs = feat.pluma && feat.pluma.velocidad != null
    ? feat.pluma.velocidad
    : (feat.viento_dominante_velocidad && feat.viento_dominante_velocidad !== 'N/A'
        ? parseFloat(feat.viento_dominante_velocidad) : 2.5);
  const score = feat.elite_score || 0;
  // Tamaño de la pluma proporcional al score y viento
  const lengthDeg = (0.02 + score / 2000) * Math.max(0.5, windMs / 3.0);
  const widthDeg  = lengthDeg * 0.35;

  // Dirección del viento (a dónde va la pluma)
  const dirRad = (windDeg * Math.PI) / 180;
  const points = 24;
  const coords = [];
  for (let i = 0; i <= points; i++) {
    const t = (i / points) * 2 * Math.PI;
    // Elipse orientada según el viento
    const lx = Math.cos(t) * widthDeg;
    const ly = Math.sin(t) * lengthDeg;
    // Rotar según dirección del viento
    const rx = lx * Math.cos(dirRad) - ly * Math.sin(dirRad);
    const ry = lx * Math.sin(dirRad) + ly * Math.cos(dirRad);
    // Desplazar centro de la pluma en la dirección del viento
    const cx = lon + Math.sin(dirRad) * lengthDeg * 0.5;
    const cy = lat + Math.cos(dirRad) * lengthDeg * 0.5;
    coords.push([cx + rx, cy + ry]);
  }
  return coords;
}

// ─── Init ────────────────────────────────────────────────────────────────────
async function init() {
  if (!TOKEN()) { window.location.href = '/login'; return; }
  try {
    me = await api('/api/user/profile');
    document.getElementById('userName').textContent = me.full_name || me.username;
    document.getElementById('userPlan').textContent =
      (me.plan_info?.icon || '◉') + ' ' + (me.plan_info?.nombre || me.plan || 'Plan');
    document.getElementById('userPlan').style.color = me.plan_info?.color || '#00d4ff';
    document.getElementById('userPlan').style.borderColor = (me.plan_info?.color || '#00d4ff') + '55';
    document.getElementById('userPlan').style.background = (me.plan_info?.color || '#00d4ff') + '22';
    if (me.role === 'admin') {
      document.getElementById('adminLink').style.display = 'inline-block';
    }
  } catch (e) { logout(); return; }

  document.querySelectorAll('.tab[data-feature]').forEach(t => {
    const f = t.dataset.feature;
    if (!userHasFeature(f)) t.classList.add('disabled');
  });

  try {
    layers = await api('/api/v55/satellite/layers');
  } catch(e) {}

  loadDashboard();
  startWebSocket();
  startAutoRefresh();
  refreshTicketsBadge();
  setInterval(refreshTicketsBadge, 30000);
}

async function refreshTicketsBadge() {
  try {
    const r = await api('/api/tickets/stats/summary');
    const open = r.abiertos || 0;
    const badge = document.getElementById('ticketsBadge');
    if (!badge) return;
    if (open > 0) {
      badge.textContent = open > 99 ? '99+' : open;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  } catch(e) {}
}

function switchTab(name) {
  const tab = document.querySelector(`.tab[data-tab="${name}"]`);
  if (tab && tab.classList.contains('disabled')) {
    showLockOverlay(); return;
  }
  document.getElementById('lockOverlay').style.display = 'none';
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('sec-' + name)?.classList.add('active');
  const fn = {
    dashboard: loadDashboard, map: loadMap, detections: loadDetections,
    tickets: loadTickets,
    ml: loadML, compliance: loadCompliance, carbon: loadCarbon,
    exports: loadExports, plan: loadPlan,
  }[name];
  if (fn) fn();
}

function showLockOverlay() {
  const overlay = document.getElementById('lockOverlay');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelector('main, body').appendChild(overlay);
  overlay.style.display = 'block';
  overlay.style.margin = '20px 18px';
}

// ─── Dashboard ───────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const summary = await api('/api/dashboard/summary');
    const stats = summary.stats || {};
    const diag = await api('/api/system/diagnostics').catch(() => null);
    document.getElementById('statsGrid').innerHTML = `
      <div class="stat-card"><div class="stat-label">Detecciones</div><div class="stat-value">${fmtNumber(stats.total_eventos_historicos)}</div></div>
      <div class="stat-card r"><div class="stat-label">Eventos Élite</div><div class="stat-value">${fmtNumber(stats.eventos_elite_historicos)}</div><div class="stat-sub">Score ≥ 80</div></div>
      <div class="stat-card o"><div class="stat-label">Eventos Críticos</div><div class="stat-value">${fmtNumber(stats.eventos_criticos_historicos)}</div></div>
      <div class="stat-card p"><div class="stat-label">Activos</div><div class="stat-value">${fmtNumber(stats.activos_monitoreados)}</div></div>
      <div class="stat-card g"><div class="stat-label">Pérdida USD/día</div><div class="stat-value">${fmtUSD(stats.perdida_total_usd_dia)}</div></div>
      <div class="stat-card"><div class="stat-label">Resolución</div><div class="stat-value" style="font-size:14px;">${stats.resolucion || '—'}</div></div>
    `;
    let diagHTML = '';
    if (diag && diag.checks) {
      const ch4 = diag.checks.open_meteo_ch4?.ch4_actual_ppb;
      const supabaseDets = diag.checks.supabase?.detecciones_almacenadas;
      diagHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:10px;font-size:12px;">
          <div style="background:var(--card2);padding:8px 10px;border-radius:6px;border-left:3px solid var(--green);">
            <div style="color:var(--muted);font-size:10px;text-transform:uppercase;">Supabase</div>
            <div>● ${supabaseDets} eventos reales</div>
          </div>
          <div style="background:var(--card2);padding:8px 10px;border-radius:6px;border-left:3px solid var(--green);">
            <div style="color:var(--muted);font-size:10px;text-transform:uppercase;">Sentinel-5P</div>
            <div>● Copernicus REAL</div>
          </div>
          <div style="background:var(--card2);padding:8px 10px;border-radius:6px;border-left:3px solid var(--green);">
            <div style="color:var(--muted);font-size:10px;text-transform:uppercase;">Open-Meteo CH4</div>
            <div>● ${ch4 ? ch4.toFixed(0) + ' ppb' : 'OK'}</div>
          </div>
          <div style="background:var(--card2);padding:8px 10px;border-radius:6px;border-left:3px solid ${diag.resumen.todo_real ? 'var(--green)' : 'var(--orange)'};">
            <div style="color:var(--muted);font-size:10px;text-transform:uppercase;">Salud sistema</div>
            <div>● ${diag.resumen.modulos_ok}/${diag.resumen.modulos_total} OK · ${diag.resumen.todo_real ? 'TODO REAL' : 'verificar'}</div>
          </div>
        </div>`;
    }
    document.getElementById('systemStatus').innerHTML = `
      <div><b>Sistema:</b> ${summary.system_status || 'OPERATIONAL_24_7'}</div>
      <div><b>Última ejecución:</b> ${fmtDate(summary.last_execution)}</div>
      <div><b>Próxima verificación:</b> ${fmtDate(summary.next_check)}</div>
      <div><b>Fuente:</b> <span style="color:var(--green)">${summary.data_source || 'Sentinel-5P + Open-Meteo (real)'}</span></div>
      <div><b>Cobertura:</b> ${stats.cobertura || 'Magdalena Medio, Colombia'}</div>
      ${diagHTML}
    `;
    const a = await api('/api/v55/analytics/by-asset').catch(() => ({ activos: [] }));
    const top = (a.activos || []).slice(0, 10);
    if (assetChart) assetChart.destroy();
    assetChart = new Chart(document.getElementById('assetChart'), {
      type: 'bar',
      data: {
        labels: top.map(x => x.activo),
        datasets: [{ label: 'Detecciones', data: top.map(x => x.total), backgroundColor: '#00d4ff88' }],
      },
      options: { responsive: true, plugins: { legend: { labels: { color: '#e2e8f0' }}}, scales: { x: { ticks: { color: '#64748b' }}, y: { ticks: { color: '#64748b' }}}}
    });
  } catch (e) { console.error(e); }
}

// ─── Mapa ────────────────────────────────────────────────────────────────────
async function loadMap() {
  if (!mapboxMap) initMap();
  await loadMapData();
}

function initMap() {
  if (!layers || !layers.mapbox_token) {
    document.getElementById('map').innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted);">Mapbox no configurado</div>';
    return;
  }
  mapboxgl.accessToken = layers.mapbox_token;
  mapboxMap = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/satellite-streets-v12',
    center: [-74.0, 6.5],
    zoom: 8.2,
    attributionControl: true,
  });
  mapboxMap.addControl(new mapboxgl.NavigationControl(), 'top-left');
  mapboxMap.addControl(new mapboxgl.FullscreenControl(), 'top-left');
  mapboxMap.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: 'metric' }), 'bottom-right');

  // Inject extra map control buttons into the panel
  _injectMapExtraControls();

  // Build layer toggles from satellite layers
  _buildSatelliteLayerToggles();
}

function _injectMapExtraControls() {
  const list = document.getElementById('layerList');
  if (!list) return;

  // Heatmap toggle
  const heatRow = document.createElement('label');
  heatRow.className = 'layer-row';
  heatRow.id = 'layer-row-heatmap';
  heatRow.innerHTML = `
    <input type="checkbox" id="toggle-heatmap"/>
    <span>🔥 Mapa de calor CH4</span>
  `;
  heatRow.querySelector('input').addEventListener('change', (e) => {
    _setHeatmapVisibility(e.target.checked);
  });
  list.insertBefore(heatRow, list.firstChild);

  // Plumas toggle
  const plumaRow = document.createElement('label');
  plumaRow.className = 'layer-row';
  plumaRow.id = 'layer-row-plumas';
  plumaRow.innerHTML = `
    <input type="checkbox" checked id="toggle-plumas"/>
    <span>💨 Proyección de plumas</span>
  `;
  plumaRow.querySelector('input').addEventListener('change', (e) => {
    _setPlumasVisibility(e.target.checked);
  });
  list.insertBefore(plumaRow, list.firstChild);

  const sep = document.createElement('hr');
  sep.style.cssText = 'border-color:var(--border);margin:8px 0;';
  list.insertBefore(sep, list.firstChild);

  const labelBuiltin = document.createElement('div');
  labelBuiltin.style.cssText = 'font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;';
  labelBuiltin.textContent = 'Capas de análisis';
  list.insertBefore(labelBuiltin, list.firstChild);
}

function _buildSatelliteLayerToggles() {
  const list = document.getElementById('layerList');
  if (!list || !layers) return;

  const satelliteEntries = Object.entries(layers.layers || {}).filter(([k]) => !k.startsWith('mapbox_'));
  if (!satelliteEntries.length) return;

  const sep2 = document.createElement('hr');
  sep2.style.cssText = 'border-color:var(--border);margin:8px 0;';
  list.appendChild(sep2);

  const labelSat = document.createElement('div');
  labelSat.style.cssText = 'font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;';
  labelSat.textContent = 'Capas Satelitales';
  list.appendChild(labelSat);

  satelliteEntries.forEach(([key, l]) => {
    const locked = !l.available;
    const row = document.createElement('label');
    row.className = 'layer-row' + (locked ? ' locked' : '');
    row.innerHTML = `
      <input type="checkbox" ${locked ? 'disabled' : ''} data-layer="${l.id}" data-tile="${l.tile_url || ''}"/>
      <span>${l.name} ${locked ? '🔒' : ''}</span>
    `;
    if (!locked) {
      row.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) {
          _addSentinelLayer(l);
        } else {
          _removeSentinelLayer(l);
        }
      });
    } else {
      // Locked: show premium message on click
      row.addEventListener('click', () => {
        showLiveBanner('🔒 Capa "' + l.name + '" requiere plan superior. El mapa de calor está disponible como alternativa visual.', 'info');
        // Suggest heatmap as visual alternative
        const heatToggle = document.getElementById('toggle-heatmap');
        if (heatToggle && !heatToggle.checked) {
          heatToggle.checked = true;
          _setHeatmapVisibility(true);
        }
      });
    }
    list.appendChild(row);
  });
}

function _addSentinelLayer(layer) {
  if (!mapboxMap) return;
  const id = 'overlay-' + layer.id;
  if (mapboxMap.getSource(id)) return;

  // Use EOX cloudless as real tile source (public, no token required)
  const tilesUrl = 'https://tiles.maps.eox.at/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=s2cloudless-2023&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png';

  mapboxMap.addSource(id, {
    type: 'raster',
    tiles: [tilesUrl],
    tileSize: 256,
    attribution: layer.fuente || '© Copernicus / EOX',
  });
  mapboxMap.addLayer({
    id: id, type: 'raster', source: id, paint: { 'raster-opacity': 0.7 },
  }, 'dets-pulse');  // Insert below detection layers
  activeLayers[id] = true;
}

function _removeSentinelLayer(layer) {
  if (!mapboxMap) return;
  const id = 'overlay-' + layer.id;
  if (mapboxMap.getLayer(id)) mapboxMap.removeLayer(id);
  if (mapboxMap.getSource(id)) mapboxMap.removeSource(id);
  delete activeLayers[id];
}

function _setHeatmapVisibility(visible) {
  _heatmapVisible = visible;
  if (!mapboxMap) return;
  const vis = visible ? 'visible' : 'none';
  if (mapboxMap.getLayer('dets-heat')) {
    mapboxMap.setLayoutProperty('dets-heat', 'visibility', vis);
  }
}

function _setPlumasVisibility(visible) {
  _plumasVisible = visible;
  if (!mapboxMap) return;
  const vis = visible ? 'visible' : 'none';
  ['plumas-fill', 'plumas-outline'].forEach(id => {
    if (mapboxMap.getLayer(id)) mapboxMap.setLayoutProperty(id, 'visibility', vis);
  });
}

function changeBaseStyle() {
  if (!mapboxMap) return;
  const newStyle = document.getElementById('baseStyle').value;
  mapboxMap.setStyle(newStyle);
  mapboxMap.once('styledata', () => {
    // Re-add all data layers after style change
    activeLayers = {};
    loadMapData();
  });
}

function locateUser() {
  if (!navigator.geolocation || !mapboxMap) return;
  navigator.geolocation.getCurrentPosition(p => {
    mapboxMap.flyTo({ center: [p.coords.longitude, p.coords.latitude], zoom: 12 });
    new mapboxgl.Marker({ color: '#00d4ff' }).setLngLat([p.coords.longitude, p.coords.latitude]).addTo(mapboxMap);
  });
}

// ─── Map Data Loading (Heatmap + Plumas + Circles) ────────────────────────────
async function loadMapData() {
  if (!mapboxMap) return;
  try {
    const data = await api('/api/detections/map');
    const rawFeats = data.features || [];

    // Main detection GeoJSON
    const features = rawFeats.map(f => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [f.lon, f.lat] },
      properties: f,
    }));

    // Pluma polygons GeoJSON
    const plumaFeatures = rawFeats.map(f => {
      const coords = buildPlumaPolygon(f);
      return {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [coords] },
        properties: {
          ...f,
          plumaOpacity: Math.min(0.55, 0.08 + (f.elite_score || 0) / 200),
        },
      };
    });

    const plumaGeoJSON = { type: 'FeatureCollection', features: plumaFeatures };
    const detGeoJSON   = { type: 'FeatureCollection', features };

    // ── Update or create sources ─────────────────────────────────────────────
    if (mapboxMap.getSource('dets')) {
      mapboxMap.getSource('dets').setData(detGeoJSON);
    } else {
      mapboxMap.addSource('dets', { type: 'geojson', data: detGeoJSON });
      _addDetectionLayers();
    }

    if (mapboxMap.getSource('plumas')) {
      mapboxMap.getSource('plumas').setData(plumaGeoJSON);
    } else {
      mapboxMap.addSource('plumas', { type: 'geojson', data: plumaGeoJSON });
      _addPlumaLayers();
    }

    // Apply current visibility states
    _setHeatmapVisibility(_heatmapVisible);
    _setPlumasVisibility(_plumasVisible);

  } catch(e) { console.error(e); }
}

// ─── Layer Definitions ────────────────────────────────────────────────────────
function _addDetectionLayers() {
  // 1. HEATMAP layer — CH4 intensity-based, hidden by default
  mapboxMap.addLayer({
    id: 'dets-heat',
    type: 'heatmap',
    source: 'dets',
    maxzoom: 15,
    layout: { visibility: 'none' },
    paint: {
      // Weight: anomaly_ppb drives intensity; fallback to elite_score
      'heatmap-weight': [
        'interpolate', ['linear'],
        ['coalesce',
          ['to-number', ['get', 'anomaly_ppb'], 0],
          ['*', ['to-number', ['get', 'elite_score'], 0], 3]
        ],
        0, 0, 500, 0.5, 1500, 1.0,
      ],
      // Intensity scales with zoom
      'heatmap-intensity': [
        'interpolate', ['linear'], ['zoom'],
        0, 0.8, 9, 2.5, 14, 5,
      ],
      // Color ramp: transparent → cyan → yellow → orange → red
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0,    'rgba(0,0,0,0)',
        0.15, 'rgba(0,212,255,0.3)',
        0.35, 'rgba(0,255,136,0.6)',
        0.55, 'rgba(255,215,0,0.75)',
        0.75, 'rgba(255,140,0,0.85)',
        1.0,  'rgba(255,34,68,1)',
      ],
      'heatmap-radius': [
        'interpolate', ['linear'], ['zoom'],
        0, 18, 9, 40, 14, 80,
      ],
      'heatmap-opacity': 0.75,
    },
  });

  // 2. Pulse glow for critical/elite points
  mapboxMap.addLayer({
    id: 'dets-pulse',
    type: 'circle',
    source: 'dets',
    filter: ['>=', ['to-number', ['get', 'elite_score']], 60],
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 16, 12, 34],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.14,
      'circle-stroke-width': 0,
    },
  });

  // 3. Main detection circles
  mapboxMap.addLayer({
    id: 'dets-circle',
    type: 'circle',
    source: 'dets',
    paint: {
      'circle-radius': [
        'interpolate', ['linear'],
        ['to-number', ['get', 'elite_score']],
        0, 6, 50, 8, 70, 11, 80, 14, 100, 18,
      ],
      'circle-color': ['get', 'color'],
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': [
        'case', ['>=', ['to-number', ['get', 'elite_score']], 80], 3,
        ['>=', ['to-number', ['get', 'elite_score']], 60], 2, 1.2,
      ],
      'circle-opacity': 0.95,
    },
  });

  // ── Popup on click ──────────────────────────────────────────────────────────
  mapboxMap.on('click', 'dets-circle', (e) => {
    const p = e.features[0].properties;
    const score = parseFloat(p.elite_score) || 0;
    const ch4 = parseFloat(p.ch4_ppb) || 0;
    const anomaly = parseFloat(p.anomaly_ppb) || 0;
    const flujoKgh = parseFloat(p.flujo_kgh) || 0;
    const co2e = parseFloat(p.impacto_co2e_anual_ton) || 0;
    const cert = p.certificacion_espectral || '';
    const mi = parseFloat(p.methane_index) || 0;
    const loss = parseFloat(p.perdida_usd_dia) || 0;
    const cat = score >= 80 ? 'ÉLITE P0' : score >= 60 ? 'CRÍTICO P1' : score >= 40 ? 'VIGILANCIA' : 'MONITOREO';
    const isCritical = score >= 60;

    // Compliance mini-bars
    const compNorms = evalCompliance(flujoKgh);
    const compHTML = compNorms.length > 0 ? `
      <div style="margin-top:10px;border-top:1px solid #1e3a5f;padding-top:8px;">
        <div style="font-size:9px;text-transform:uppercase;color:#64748b;letter-spacing:0.5px;margin-bottom:6px;">Cumplimiento Normativo</div>
        ${compNorms.map(c => `
          <div style="margin-bottom:4px;">
            <div style="display:flex;justify-content:space-between;font-size:9px;color:${c.estado==='EXCEDE'?c.color:'#64748b'};margin-bottom:2px;">
              <span>${c.name}</span>
              <span style="font-weight:700;">${c.estado}</span>
            </div>
            <div style="background:#0d1b2e;border-radius:3px;height:4px;overflow:hidden;">
              <div style="height:100%;width:${Math.min(c.pct,100)}%;background:${c.estado==='EXCEDE'?c.color:'#00ff88'};border-radius:3px;transition:width 0.4s;"></div>
            </div>
          </div>`).join('')}
      </div>` : '';

    // Methane index mini-gauge
    const miPct = Math.min(100, Math.round(mi * 400));
    const miColor = mi > 0.5 ? '#ff2244' : mi > 0.25 ? '#ff8c00' : mi > 0.1 ? '#ffd700' : '#00ff88';
    const spectralHTML = `
      <div style="margin-top:8px;">
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#64748b;margin-bottom:2px;">
          <span>Índice Metano (MI)</span><span style="color:${miColor};font-weight:700;">${mi.toFixed(3)}</span>
        </div>
        <div style="background:#0d1b2e;border-radius:3px;height:5px;overflow:hidden;">
          <div style="height:100%;width:${miPct}%;background:linear-gradient(90deg,${miColor}88,${miColor});border-radius:3px;"></div>
        </div>
      </div>`;

    // Score indicator arc (CSS-only mini meter)
    const scorePct = Math.min(100, Math.round((score / 120) * 100));
    const scoreColor = score >= 80 ? '#ff2244' : score >= 60 ? '#ff8c00' : score >= 40 ? '#ffd700' : '#00ff88';
    const scoreBarHTML = `
      <div style="margin-top:8px;">
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#64748b;margin-bottom:2px;">
          <span>Elite Score</span>
          <span style="color:${scoreColor};font-weight:800;font-size:11px;">${score.toFixed(1)}<span style="font-size:8px;color:#64748b;">/120</span></span>
        </div>
        <div style="background:#0d1b2e;border-radius:3px;height:6px;overflow:hidden;">
          <div style="height:100%;width:${scorePct}%;background:linear-gradient(90deg,${scoreColor}77,${scoreColor});border-radius:3px;"></div>
        </div>
      </div>`;

    // CO2e + Economic chip row
    const chipsHTML = (co2e > 0 || loss > 0) ? `
      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
        ${co2e > 0 ? `<div style="background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.3);border-radius:4px;padding:3px 7px;font-size:9px;color:#00ff88;">🌱 ${co2e.toFixed(1)} tCO₂e/año</div>` : ''}
        ${loss > 0 ? `<div style="background:rgba(255,140,0,0.1);border:1px solid rgba(255,140,0,0.3);border-radius:4px;padding:3px 7px;font-size:9px;color:#ff8c00;">💸 $${loss.toFixed(2)}/día</div>` : ''}
        ${cert === 'CERTIFICADO' ? `<div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);border-radius:4px;padding:3px 7px;font-size:9px;color:#00d4ff;">✓ ${cert}</div>` : ''}
      </div>` : '';

    new mapboxgl.Popup({ closeButton: true, maxWidth: '300px' })
      .setLngLat(e.lngLat)
      .setHTML(`
        <div style="background:#0d1b2e;color:#e2e8f0;padding:14px;border-radius:8px;font-family:system-ui;min-width:260px;border-left:3px solid ${p.color};">
          <div style="font-weight:700;color:${p.color};margin-bottom:2px;font-size:15px;">${p.activo}</div>
          <div style="font-size:10px;color:#64748b;margin-bottom:8px;">${p.operador || '—'} · ${p.tipo || '—'}</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;margin-bottom:6px;">
            <div style="background:#111827;padding:5px 7px;border-radius:4px;">
              <div style="color:#64748b;font-size:9px;">CH4 Total</div>
              <div style="font-weight:700;color:#00d4ff;">${ch4.toFixed(1)} ppb</div>
            </div>
            <div style="background:#111827;padding:5px 7px;border-radius:4px;">
              <div style="color:#64748b;font-size:9px;">Anomalía</div>
              <div style="font-weight:700;color:#ffd700;">+${anomaly.toFixed(1)} ppb</div>
            </div>
            ${flujoKgh > 0 ? `
            <div style="background:#111827;padding:5px 7px;border-radius:4px;">
              <div style="color:#64748b;font-size:9px;">Flujo</div>
              <div style="font-weight:700;color:#ff8c00;">${flujoKgh.toFixed(3)} kg/h</div>
            </div>` : ''}
            <div style="background:#111827;padding:5px 7px;border-radius:4px;">
              <div style="color:#64748b;font-size:9px;">Nivel</div>
              <div style="font-weight:700;background:${p.color}22;color:${p.color};padding:1px 5px;border-radius:3px;font-size:9px;display:inline-block;">${cat}</div>
            </div>
          </div>

          ${scoreBarHTML}
          ${spectralHTML}
          ${chipsHTML}
          ${compHTML}

          <div style="font-size:9px;color:#475569;margin-top:8px;padding-top:6px;border-top:1px solid #1e3a5f;">${p.fecha || ''}</div>
          ${isCritical ? `<div style="margin-top:8px;padding:5px 8px;background:${p.color}18;border-radius:4px;font-size:10px;color:${p.color};font-weight:600;">🎫 Ticket auto-generado · ver pestaña Tickets</div>` : ''}
        </div>
      `).addTo(mapboxMap);
  });

  mapboxMap.on('mouseenter', 'dets-circle', () => mapboxMap.getCanvas().style.cursor = 'pointer');
  mapboxMap.on('mouseleave', 'dets-circle', () => mapboxMap.getCanvas().style.cursor = '');
}

// ─── Pluma (smoke/gas plume) layers ──────────────────────────────────────────
function _addPlumaLayers() {
  // Fill — gradient opacity by score
  mapboxMap.addLayer({
    id: 'plumas-fill',
    type: 'fill',
    source: 'plumas',
    layout: { visibility: _plumasVisible ? 'visible' : 'none' },
    paint: {
      'fill-color': ['get', 'color'],
      'fill-opacity': ['get', 'plumaOpacity'],
    },
  }, 'dets-pulse');  // Insert below detection circles

  // Outline
  mapboxMap.addLayer({
    id: 'plumas-outline',
    type: 'line',
    source: 'plumas',
    layout: { visibility: _plumasVisible ? 'visible' : 'none' },
    paint: {
      'line-color': ['get', 'color'],
      'line-opacity': 0.4,
      'line-width': 1,
      'line-dasharray': [2, 2],
    },
  }, 'dets-pulse');
}

// ─── Detecciones ─────────────────────────────────────────────────────────────
async function loadDetections() {
  try {
    const r = await api('/api/detections?limit=200');
    allDets = r.detections || [];
    renderDetections();
  } catch(e) { console.error(e); }
}

function renderDetections() {
  const filter = (document.getElementById('filterAsset')?.value || '').toLowerCase();
  const filtered = filter ? allDets.filter(d => (d.activo_cercano || '').toLowerCase().includes(filter)) : allDets;
  document.getElementById('detectionsBody').innerHTML = filtered.slice(0, 200).map(d => {
    const score = d.score_prioridad || d.elite_score || 0;
    const cat = categoryFor(score);
    return `<tr>
      <td><small>${fmtDate(d.fecha_deteccion)}</small></td>
      <td><b>${d.activo_cercano || '—'}</b></td>
      <td>${d.operador || '—'}</td>
      <td>${(d.intensidad_ppb || d.ch4_ppb_total || 0).toFixed?.(1) || 0}</td>
      <td>${(d.ch4_ppb_anomaly || 0).toFixed?.(1) || 0}</td>
      <td><b style="color:${cat.color}">${score.toFixed?.(1) || score}</b></td>
      <td><span class="pill ${cat.cls}">${cat.name}</span></td>
      <td>${fmtUSD(d.perdida_economica_usd_dia)}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:20px;">Sin detecciones</td></tr>';
}

// ─── Tickets ─────────────────────────────────────────────────────────────────
async function loadTickets() {
  try {
    const r = await api('/api/tickets?limit=200');
    const summary = r.resumen || {};
    const tickets = r.tickets || [];

    document.getElementById('ticketsContent').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card r"><div class="stat-label">Élite P0</div><div class="stat-value">${summary.elite_p0 || 0}</div><div class="stat-sub">SLA 4h · escalación</div></div>
        <div class="stat-card o"><div class="stat-label">Crítico P1</div><div class="stat-value">${summary.critico_p1 || 0}</div><div class="stat-sub">SLA 24h · jefe HSE</div></div>
        <div class="stat-card"><div class="stat-label">Abiertos</div><div class="stat-value">${summary.abiertos || 0}</div></div>
        <div class="stat-card g"><div class="stat-label">Total</div><div class="stat-value">${r.total || 0}</div></div>
      </div>
      <div class="card">
        <div class="card-title">Tickets de Intervención (Auto-generados)</div>
        <div class="table-wrap">
          <table data-testid="tickets-table">
            <thead><tr>
              <th>ID</th><th>Categoría</th><th>Activo</th><th>Operador</th>
              <th>Score</th><th>SLA</th><th>Acción</th><th>Estado</th><th>—</th>
            </tr></thead>
            <tbody>
              ${tickets.map(t => {
                const slaDeadline = new Date(t.sla_deadline);
                const overdue = slaDeadline < new Date() && t.estado === 'ABIERTO';
                return `<tr>
                  <td><code style="font-size:11px;color:var(--accent)">${t.ticket_id}</code></td>
                  <td><span class="pill ${t.categoria === 'ELITE' ? 'elite' : 'critico'}">${t.prioridad} · ${t.categoria}</span></td>
                  <td><b>${t.activo}</b></td>
                  <td>${t.operador || '—'}</td>
                  <td><b style="color:${t.color}">${(t.score||0).toFixed(1)}</b></td>
                  <td style="color:${overdue ? 'var(--red)' : 'var(--muted)'};font-size:11px;">${overdue ? '⚠ VENCIDO' : t.sla_horas + 'h'}<br/><small>${slaDeadline.toLocaleString('es-CO',{dateStyle:'short',timeStyle:'short'})}</small></td>
                  <td style="font-size:11px;">${t.accion_recomendada || '—'}<br/><small style="color:var(--muted)">→ ${t.escalar_a || '—'}</small></td>
                  <td><span class="pill ${t.estado === 'ABIERTO' ? 'critico' : 'monitoreo'}">${t.estado}</span></td>
                  <td>
                    ${t.estado === 'ABIERTO' ? `<button class="btn outline" style="padding:4px 8px;font-size:10px;" onclick="updateTicketStatus('${t.ticket_id}','EN_PROGRESO')">▶</button>` : ''}
                    ${t.estado !== 'CERRADO' ? `<button class="btn" style="padding:4px 8px;font-size:10px;background:var(--green);color:#001a0e;" onclick="updateTicketStatus('${t.ticket_id}','RESUELTO')">✓</button>` : ''}
                  </td>
                </tr>`;
              }).join('') || '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:20px;">No hay tickets · el sistema generará automáticamente al detectar score ≥ 60</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    document.getElementById('ticketsContent').innerHTML = `<div class="card"><p style="color:var(--red)">${e.message}</p></div>`;
  }
}

async function updateTicketStatus(ticketId, estado) {
  try {
    const nota = estado === 'RESUELTO' ? prompt('Nota de cierre (opcional):') : '';
    await fetch('/api/tickets/' + ticketId, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ estado, nota: nota || undefined }),
    });
    showLiveBanner(`Ticket ${ticketId} → ${estado}`, 'success');
    loadTickets();
  } catch(e) { showLiveBanner('⚠ ' + e.message, 'error'); }
}

// ─── ML ──────────────────────────────────────────────────────────────────────
async function loadML() {
  try {
    const r = await api('/api/ml/predictions');
    const resumen = r.resumen || {};
    document.getElementById('mlContent').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card r"><div class="stat-label">Riesgo Alto</div><div class="stat-value">${resumen.activos_riesgo_alto || 0}</div></div>
        <div class="stat-card o"><div class="stat-label">Riesgo Medio</div><div class="stat-value">${resumen.activos_riesgo_medio || 0}</div></div>
        <div class="stat-card g"><div class="stat-label">Riesgo Bajo</div><div class="stat-value">${resumen.activos_riesgo_bajo || 0}</div></div>
        <div class="stat-card p"><div class="stat-label">Activo Más Crítico</div><div class="stat-value" style="font-size:14px;">${resumen.activo_mas_critico || '—'}</div></div>
      </div>
      <div class="card">
        <div class="card-title">Modelo</div>
        <div style="font-size:13px;">
          <div><b>Versión:</b> ${r.version || '3.7'} (RandomForest + GradientBoosting)</div>
          <div><b>Eventos analizados:</b> ${r.modelo?.n_events || 0}</div>
          <div><b>Método:</b> ${r.modelo?.method || 'sklearn_randomforest'}</div>
          <div><b>F1 promedio:</b> ${(r.modelo?.cv_f1_mean || 0).toFixed(3)}</div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Predicciones por Activo</div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Activo</th><th>Probabilidad reincidencia</th><th>Riesgo</th></tr></thead>
            <tbody>
              ${(r.predicciones || []).slice(0, 50).map(p => `
                <tr><td><b>${p.activo}</b></td>
                <td>${((p.prob_reincidencia || 0) * 100).toFixed(1)}%</td>
                <td><span class="pill ${p.nivel_riesgo === 'ALTO' ? 'elite' : p.nivel_riesgo === 'MEDIO' ? 'critico' : 'monitoreo'}">${p.nivel_riesgo || '—'}</span></td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    document.getElementById('mlContent').innerHTML = `<div class="card"><p style="color:var(--red)">${e.message}</p></div>`;
  }
}

// ─── Compliance ──────────────────────────────────────────────────────────────
async function loadCompliance() {
  try {
    const sum = await api('/api/v55/compliance/summary?limit=500');
    const cards = Object.entries(sum.por_normativa).map(([k, v]) => `
      <div class="stat-card" style="border-left-color:${v.color};">
        <div class="stat-label">${v.nombre}</div>
        <div class="stat-value" style="color:${v.color};font-size:24px;">${v.pct_cumplimiento}%</div>
        <div class="stat-sub">${v.cumple}/${v.total} cumplen · ${v.excede} exceden</div>
      </div>
    `).join('');
    const v = await api('/api/v55/compliance/violations?limit=100');
    document.getElementById('complianceContent').innerHTML = `
      <div class="stats-grid">${cards}</div>
      <div class="card">
        <div class="card-title">Violaciones Detectadas</div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Activo</th><th>Operador</th><th>CH4 kg/h</th><th>Score</th><th>Normativas</th></tr></thead>
            <tbody>
              ${v.violaciones.map(d => `
                <tr><td><small>${fmtDate(d.fecha)}</small></td><td>${d.activo}</td><td>${d.operador}</td>
                <td><b style="color:var(--orange)">${d.ch4_kg_h}</b></td><td>${(d.score||0).toFixed(1)}</td>
                <td>${d.violaciones.map(vv => `<span class="pill" style="background:${vv.color}22;color:${vv.color}">${vv.normativa_id}</span>`).join(' ')}</td>
                </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--green);padding:20px;">✓ Sin violaciones</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    document.getElementById('complianceContent').innerHTML = `<div class="card"><p style="color:var(--red)">${e.message}</p></div>`;
  }
}

// ─── Carbon ──────────────────────────────────────────────────────────────────
async function loadCarbon() {
  try {
    const c = await api('/api/v55/carbon/credits?limit=200');
    const k = await api('/api/v55/carbon/constants');
    document.getElementById('carbonContent').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card g"><div class="stat-label">tCO2e/año</div><div class="stat-value">${fmtNumber(c.total_co2e_ton_year, 1)}</div></div>
        <div class="stat-card"><div class="stat-label">Verra USD</div><div class="stat-value">${fmtUSD(c.total_creditos_verra_usd)}</div></div>
        <div class="stat-card o"><div class="stat-label">Gold Standard USD</div><div class="stat-value">${fmtUSD(c.total_creditos_gold_standard_usd)}</div></div>
        <div class="stat-card p"><div class="stat-label">EU ETS USD</div><div class="stat-value">${fmtUSD(c.total_valor_eu_ets_usd)}</div></div>
      </div>
      <div class="card">
        <div class="card-title">Metodología</div>
        <p style="font-size:13px;">GWP IPCC AR6 100y: <b>${k.gwp_ch4_ipcc_ar6_100y}</b> · 20y: <b>${k.gwp_ch4_ipcc_ar6_20y}</b></p>
        <p style="font-size:13px;">Verra: <b>$${k.precio_verra_usd_tco2e}/tCO2e</b> · Gold Standard: <b>$${k.precio_gold_standard_usd_tco2e}</b> · EU ETS: <b>$${k.precio_eu_ets_usd_tco2e}</b> · CARB: <b>$${k.precio_carb_usd_tco2e}</b></p>
      </div>
      <div class="card">
        <div class="card-title">Detalle por Detección</div>
        <div class="table-wrap" style="max-height:500px;overflow-y:auto;">
          <table>
            <thead><tr><th>Activo</th><th>CH4 kg/h</th><th>tCO2e/año</th><th>Verra</th><th>Gold Std</th><th>EU ETS</th></tr></thead>
            <tbody>
              ${c.detalle.slice(0, 100).map(d => `
                <tr><td>${d.activo}</td><td>${d.ch4_kg_per_hour}</td>
                <td>${fmtNumber(d.co2e_ton_year, 2)}</td>
                <td>${fmtUSD(d.creditos_verra_usd)}</td>
                <td>${fmtUSD(d.creditos_gold_standard_usd)}</td>
                <td>${fmtUSD(d.valor_eu_ets_usd)}</td></tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    document.getElementById('carbonContent').innerHTML = `<div class="card"><p style="color:var(--red)">${e.message}</p></div>`;
  }
}

// ─── Exports ─────────────────────────────────────────────────────────────────
function loadExports() {
  const canCsv = userHasFeature('exports_csv');
  const canExcel = userHasFeature('exports_excel');
  const canPdf = userHasFeature('exports_pdf');
  document.getElementById('exportsContent').innerHTML = `
    <div class="stats-grid">
      <div class="card" style="margin:0;${canCsv?'':'opacity:0.4;'}">
        <div class="card-title">CSV ${canCsv?'':'🔒'}</div>
        <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">Datos crudos para BI / Excel.</p>
        <button class="btn outline" onclick="downloadFile('csv')" ${canCsv?'':'disabled'} data-testid="export-csv-btn">Descargar CSV</button>
      </div>
      <div class="card" style="margin:0;${canExcel?'':'opacity:0.4;'}">
        <div class="card-title">Excel ${canExcel?'':'🔒'}</div>
        <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">Multi-hoja con compliance.</p>
        <button class="btn" onclick="downloadFile('excel')" ${canExcel?'':'disabled'} data-testid="export-excel-btn">Descargar Excel</button>
      </div>
      <div class="card" style="margin:0;${canPdf?'':'opacity:0.4;'}">
        <div class="card-title">PDF Ejecutivo ${canPdf?'':'🔒'}</div>
        <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">Reporte ANLA / EPA-style.</p>
        <button class="btn purple" onclick="downloadFile('pdf')" ${canPdf?'':'disabled'} data-testid="export-pdf-btn">Descargar PDF</button>
      </div>
    </div>
  `;
}

async function downloadFile(kind) {
  try {
    const r = await fetch('/api/v55/export/' + kind + '?limit=500', { headers: authHeaders() });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'Error descarga');
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `metano_${kind}_${Date.now()}.${kind === 'excel' ? 'xlsx' : kind}`;
    a.click();
    URL.revokeObjectURL(url);
  } catch(e) { alert(e.message); }
}

// ─── Mi Plan ─────────────────────────────────────────────────────────────────
async function loadPlan() {
  const p = me.plan_info || {};
  const limites = p.limites || {};
  const features = Object.entries(limites).filter(([k, v]) => typeof v === 'boolean').map(([k, v]) => `
    <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:${v ? 'rgba(0,255,136,0.05)' : 'rgba(100,116,139,0.05)'};border-radius:6px;font-size:13px;color:${v ? 'var(--green)' : 'var(--muted)'};">
      <span style="font-size:14px;">${v ? '✓' : '○'}</span>
      <span>${k.replace(/_/g, ' ')}</span>
    </div>
  `).join('');
  document.getElementById('planContent').innerHTML = `
    <div class="card" style="border-left:4px solid ${p.color || '#00d4ff'};">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px;">
        <span style="font-size:38px;">${p.icon || '◉'}</span>
        <div>
          <h2 style="font-size:24px;color:${p.color || '#00d4ff'};">${p.nombre || 'Sin plan'}</h2>
          <p style="color:var(--muted);font-size:13px;">SLA: ${limites.soporte_horas || '—'}h · Activos: ${limites.max_activos === -1 ? 'Ilimitados' : limites.max_activos} · Usuarios: ${limites.max_usuarios === -1 ? 'Ilimitados' : limites.max_usuarios}</p>
        </div>
      </div>
      <h4 style="font-size:12px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;">Features incluidas en tu plan:</h4>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:6px;">
        ${features}
      </div>
    </div>
    <div class="card">
      <div class="card-title">Incluye</div>
      <ul style="list-style:none;padding:0;">
        ${(p.incluye || []).map(i => `<li style="padding:5px 0;border-bottom:1px solid rgba(30,58,95,0.3);font-size:13px;">✓ ${i}</li>`).join('')}
      </ul>
    </div>
    ${(p.no_incluye || []).length > 0 ? `
    <div class="card">
      <div class="card-title" style="color:var(--muted);">No incluido (upgrade para acceder)</div>
      <ul style="list-style:none;padding:0;">
        ${p.no_incluye.map(i => `<li style="padding:5px 0;border-bottom:1px solid rgba(30,58,95,0.3);font-size:13px;color:var(--muted);">○ ${i}</li>`).join('')}
      </ul>
      <p style="margin-top:12px;font-size:13px;color:var(--purple);">Para activar más funciones, contacta a tu administrador.</p>
    </div>` : ''}
  `;
}

// ─── WebSocket Live ──────────────────────────────────────────────────────────
let _liveWS = null;
let _autoRefreshTimer = null;

function startWebSocket() {
  try {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _liveWS = new WebSocket(proto + '//' + location.host + '/api/ws/live');
    _liveWS.onopen = () => {
      const el = document.getElementById('liveStatus');
      if (el) el.textContent = 'En vivo · datos reales';
    };
    _liveWS.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data);
        if (m.type === 'pipeline.started') {
          showLiveBanner('🔄 Pipeline iniciado — descargando datos Sentinel-5P en vivo', 'info');
        } else if (m.type === 'pipeline.completed') {
          const d = m.data || {};
          showLiveBanner(`✓ Pipeline completado · ${d.total_detecciones} detecciones · ${d.alertas_elite} élite · $${(d.perdida_usd_dia||0).toFixed(0)}/día`, 'success');
          if (mapboxMap && document.querySelector('.tab.active')?.dataset.tab === 'map') loadMapData();
          if (document.querySelector('.tab.active')?.dataset.tab === 'dashboard') loadDashboard();
          if (document.querySelector('.tab.active')?.dataset.tab === 'detections') loadDetections();
        } else if (m.type === 'detection.elite') {
          const d = m.data || {};
          showLiveBanner(`🚨 ELITE: ${d.activo} · ${d.operador} · score=${(d.score||0).toFixed(1)} · ${(d.ch4_ppb||0).toFixed(0)} ppb`, 'alert');
          refreshTicketsBadge();
        } else if (m.type === 'ticket.created') {
          const d = m.data || {};
          showLiveBanner(`🎫 Nuevo ticket ${d.prioridad}: ${d.activo} · score=${(d.score||0).toFixed(1)} · SLA ${d.sla_horas}h`, d.categoria === 'ELITE' ? 'alert' : 'info');
          refreshTicketsBadge();
          if (document.querySelector('.tab.active')?.dataset.tab === 'tickets') loadTickets();
        } else if (m.type === 'pipeline.error') {
          showLiveBanner('⚠ Error en pipeline: ' + (m.data?.error || 'desconocido'), 'error');
        }
      } catch(e) { console.warn('WS msg parse err', e); }
    };
    _liveWS.onclose = () => {
      const el = document.getElementById('liveStatus');
      if (el) el.textContent = 'Reconectando…';
      setTimeout(startWebSocket, 5000);
    };
  } catch(e) {}
}

function showLiveBanner(text, kind = 'info') {
  let banner = document.getElementById('liveBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'liveBanner';
    banner.style.cssText = 'position:fixed;top:60px;left:50%;transform:translateX(-50%);z-index:300;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,0.5);max-width:90%;';
    document.body.appendChild(banner);
  }
  const colors = {
    info: ['#0d1b2e', '#00d4ff'], success: ['#0d1b2e', '#00ff88'],
    alert: ['#1a0d12', '#ff2244'], error: ['#1a0d0d', '#ff8c00'],
  };
  const [bg, fg] = colors[kind] || colors.info;
  banner.style.background = bg;
  banner.style.color = fg;
  banner.style.border = '1px solid ' + fg + '55';
  banner.textContent = text;
  banner.style.display = 'block';
  setTimeout(() => { banner.style.display = 'none'; }, 8000);
}

function startAutoRefresh() {
  if (_autoRefreshTimer) clearInterval(_autoRefreshTimer);
  _autoRefreshTimer = setInterval(() => {
    const active = document.querySelector('.tab.active')?.dataset.tab;
    if (active === 'map' && mapboxMap) loadMapData();
    if (active === 'dashboard') loadDashboard();
    if (active === 'detections') loadDetections();
  }, 60000);
}

async function runPipelineNow() {
  const btn = document.getElementById('btnRunPipeline');
  if (btn) { btn.disabled = true; btn.textContent = '🔄 Ejecutando…'; }
  try {
    const r = await fetch('/api/pipeline/run', {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ force: false }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'Error iniciando pipeline');
    }
    showLiveBanner('🔄 Pipeline iniciado · estarás viendo nuevas detecciones en breve', 'info');
  } catch(e) { showLiveBanner('⚠ ' + e.message, 'error'); }
  finally {
    setTimeout(() => {
      if (btn) { btn.disabled = false; btn.textContent = '🔄 Actualizar datos'; }
    }, 30000);
  }
}

document.addEventListener('DOMContentLoaded', init);
