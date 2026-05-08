// admin.js — Lógica del Panel Admin v5.5 (solo gestión de usuarios/planes/audit/health)
const API = '';
const TOKEN = () => localStorage.getItem('msr_token');
let currentUser = null;
let ws = null;
let _activosCache = [];
let _plansCache = [];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function authHeaders() {
  return { Authorization: 'Bearer ' + TOKEN(), 'Content-Type': 'application/json' };
}

async function api(path, opts = {}) {
  const r = await fetch(API + path, { ...opts, headers: { ...authHeaders(), ...(opts.headers || {}) }});
  if (r.status === 401) { logout(); throw new Error('No autorizado'); }
  if (!r.ok) {
    let detail = 'Error ' + r.status;
    try { const j = await r.json(); detail = j.detail || JSON.stringify(j); } catch(e){}
    throw new Error(detail);
  }
  const ct = r.headers.get('content-type') || '';
  return ct.includes('json') ? r.json() : r.text();
}

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  document.getElementById('toastStack').appendChild(el);
  setTimeout(() => el.remove(), 4500);
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

function logout() {
  api('/api/auth/logout', { method: 'POST' }).catch(() => {});
  localStorage.clear();
  window.location.href = '/login';
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  if (!TOKEN()) { window.location.href = '/login'; return; }
  try {
    currentUser = await api('/api/user/profile');
    document.getElementById('userName').textContent = currentUser.full_name || currentUser.username;
    document.getElementById('userRole').textContent = (currentUser.role || 'viewer').toUpperCase();
    if (currentUser.role !== 'admin') {
      toast('Acceso denegado. Se requiere rol admin.', 'error');
      setTimeout(() => window.location.href = '/app', 1200);
      return;
    }
  } catch (e) {
    logout();
    return;
  }
  // Pre-cargar planes
  try {
    const r = await api('/api/v55/plans');
    _plansCache = r.planes || [];
  } catch(e) {}
  loadDashboard();
  startWebSocket();
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
  document.querySelectorAll('.nav-item').forEach(n =>
    n.classList.toggle('active', n.dataset.tab === name));
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById('sec-' + name);
  if (sec) sec.classList.add('active');
  const fn = {
    dashboard: loadDashboard, users: loadUsers, plans: loadPlans,
    tickets: loadAdminTickets, scheduler: loadSchedulerStatus,
    audit: loadAudit, health: loadHealth,
  }[name];
  if (fn) fn();
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const stats = await api('/api/admin/stats');
    const status = await api('/api/status');
    const summary = await api('/api/dashboard/summary');
    const diag = await api('/api/system/diagnostics').catch(() => null);
    const planCounts = {};
    try {
      const users = await api('/api/admin/users');
      users.forEach(u => { if (u.role !== 'admin') planCounts[u.plan || 'regional'] = (planCounts[u.plan || 'regional'] || 0) + 1; });
    } catch(e) {}
    document.getElementById('dashStats').innerHTML = `
      <div class="stat-card"><div class="stat-label">Usuarios Totales</div><div class="stat-value" data-testid="stat-total-users">${stats.total_usuarios}</div><div class="stat-sub">${stats.usuarios_activos} activos</div></div>
      <div class="stat-card success"><div class="stat-label">Detecciones Hist.</div><div class="stat-value">${fmtNumber(summary.stats.total_eventos_historicos)}</div></div>
      <div class="stat-card warning"><div class="stat-label">Eventos Élite</div><div class="stat-value">${fmtNumber(summary.stats.eventos_elite_historicos)}</div><div class="stat-sub">Score ≥ 80</div></div>
      <div class="stat-card danger"><div class="stat-label">Eventos Críticos</div><div class="stat-value">${fmtNumber(summary.stats.eventos_criticos_historicos)}</div></div>
      <div class="stat-card purple"><div class="stat-label">Activos</div><div class="stat-value">${stats.total_activos}</div></div>
      <div class="stat-card"><div class="stat-label">Auditoría</div><div class="stat-value">${fmtNumber(stats.acciones_auditadas)}</div><div class="stat-sub">acciones</div></div>
      <div class="stat-card"><div class="stat-label">Plan Regional</div><div class="stat-value" style="color:#00d4ff;">${planCounts.regional || 0}</div></div>
      <div class="stat-card warning"><div class="stat-label">Plan Operacional</div><div class="stat-value">${planCounts.operacional || 0}</div></div>
      <div class="stat-card purple"><div class="stat-label">Plan Enterprise</div><div class="stat-value">${planCounts.enterprise || 0}</div></div>
    `;
    const mods = status.modules || {};
    document.getElementById('modulesGrid').innerHTML = Object.entries(mods).map(([k, v]) => `
      <div style="background:var(--card2);padding:12px;border-radius:8px;border:1px solid var(--border);">
        <div style="font-size:11px;color:var(--muted);text-transform:uppercase;">${k}</div>
        <div style="font-size:18px;font-weight:700;color:${v ? 'var(--green)' : 'var(--red)'};">${v ? '● ACTIVO' : '○ N/A'}</div>
      </div>
    `).join('');
    let diagHTML = '';
    if (diag && diag.resumen) {
      diagHTML = `
        <div style="margin-top:12px;padding:10px 12px;background:var(--card2);border-radius:6px;border-left:3px solid ${diag.resumen.todo_real ? 'var(--green)' : 'var(--orange)'};font-size:12px;">
          <b>Diagnóstico en vivo:</b> ${diag.resumen.modulos_ok}/${diag.resumen.modulos_total} módulos OK ·
          ${diag.resumen.todo_real ? '✓ TODO REAL · ningún dato simulado' : '⚠ verificar'} ·
          ${diag.checks.supabase?.detecciones_almacenadas || 0} detecciones reales en Supabase ·
          CH4 actual: ${(diag.checks.open_meteo_ch4?.ch4_actual_ppb || 0).toFixed(0)} ppb
        </div>`;
    }
    document.getElementById('lastExecution').innerHTML = `
      <div><b>Última ejecución:</b> ${fmtDate(status.last_execution)}</div>
      <div><b>Próxima verificación:</b> ${fmtDate(status.next_check)}</div>
      <div><b>Fuente:</b> <span style="color:var(--green)">${status.data_source || 'N/A'}</span></div>
      <div><b>Base de datos:</b> ${status.database === 'supabase' ? '🟢 Supabase (cloud)' : '🟡 JSON local'}</div>
      ${diagHTML}
      <div style="margin-top:12px;">
        <button class="btn" id="btnRunPipelineAdmin" onclick="runPipelineAdmin()" data-testid="btn-run-pipeline-admin">🔄 Ejecutar pipeline ahora</button>
      </div>
    `;
  } catch (e) { toast(e.message, 'error'); }
}

async function runPipelineAdmin() {
  const btn = document.getElementById('btnRunPipelineAdmin');
  if (btn) { btn.disabled = true; btn.textContent = '🔄 Ejecutando…'; }
  try {
    await api('/api/pipeline/run', { method: 'POST', body: JSON.stringify({ force: false }) });
    toast('Pipeline iniciado · escucha el WebSocket abajo', 'success');
  } catch(e) { toast(e.message, 'error'); }
  finally {
    setTimeout(() => {
      if (btn) { btn.disabled = false; btn.textContent = '🔄 Ejecutar pipeline ahora'; }
    }, 30000);
  }
}

// ─── Users ────────────────────────────────────────────────────────────────────
async function loadUsers() {
  try {
    const users = await api('/api/admin/users');
    const assets = await api('/api/admin/assets');
    _activosCache = assets.activos || [];
    document.getElementById('usersTbody').innerHTML = users.map(u => {
      const planObj = _plansCache.find(p => p.id === u.plan) || {};
      const planColor = planObj.color || '#64748b';
      return `
      <tr>
        <td><b>${u.username}</b><br/><small style="color:var(--muted);">${u.full_name || ''} ${u.email ? '· ' + u.email : ''}</small></td>
        <td>${u.empresa || '—'}</td>
        <td><span class="pill ${u.role}">${u.role_icon || ''} ${u.role}</span></td>
        <td>${u.role === 'admin' ? '<span class="pill admin">N/A</span>' : `<span class="pill" style="background:${planColor}22;color:${planColor};border:1px solid ${planColor}55;">${planObj.icon || ''} ${planObj.nombre || u.plan || 'regional'}</span>`}</td>
        <td>${(u.activos_asignados || []).slice(0,2).join(', ')}${(u.activos_asignados||[]).length>2?'…':''} <small style="color:var(--muted);">(${(u.activos_asignados||[]).length})</small></td>
        <td><span class="pill ${u.active ? 'active' : 'inactive'}">${u.active ? 'Activo' : 'Inactivo'}</span></td>
        <td><small>${fmtDate(u.last_login)}</small></td>
        <td>
          <button class="btn sm" onclick="openEditUser('${u.username}')" data-testid="user-edit-${u.username}">Editar</button>
          <button class="btn sm warning" onclick="openResetPass('${u.username}')" data-testid="user-reset-${u.username}">🔑</button>
          <button class="btn sm outline" onclick="toggleUser('${u.username}')" data-testid="user-toggle-${u.username}">⏻</button>
          ${u.username !== currentUser.username ? `<button class="btn sm danger" onclick="deleteUser('${u.username}')" data-testid="user-delete-${u.username}">✕</button>` : ''}
        </td>
      </tr>`;
    }).join('');
  } catch (e) { toast(e.message, 'error'); }
}

function planSelectHTML(selected = 'regional') {
  return _plansCache.map(p => `
    <option value="${p.id}" ${selected === p.id ? 'selected' : ''}>
      ${p.icon} ${p.nombre} — $${p.precio_mensual_usd}/mes
    </option>
  `).join('');
}

function openCreateUser() {
  showModal('Crear Usuario', `
    <div class="form-row">
      <div class="form-group"><label>Usuario *</label><input id="m_username" data-testid="modal-username-input" placeholder="juan.perez"/></div>
      <div class="form-group"><label>Email corporativo</label><input id="m_email" type="email" data-testid="modal-email-input" placeholder="juan@empresa.com"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Nombre completo</label><input id="m_fullname" data-testid="modal-fullname-input"/></div>
      <div class="form-group"><label>Empresa</label><input id="m_empresa" data-testid="modal-empresa-input" placeholder="Ecopetrol"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Rol *</label>
        <select id="m_role" data-testid="modal-role-select">
          <option value="viewer">Viewer (solo lectura)</option>
          <option value="operador">Operador (gestión)</option>
          <option value="admin">Admin (control total)</option>
        </select>
      </div>
      <div class="form-group"><label>Plan *</label>
        <select id="m_plan" data-testid="modal-plan-select">${planSelectHTML('regional')}</select>
      </div>
    </div>
    <div class="form-group"><label>Contraseña (mín 8) *</label><input id="m_pass" type="password" data-testid="modal-password-input"/></div>
    <div class="form-group"><label>Activos asignados</label>
      <div class="checkbox-grid">
        ${_activosCache.map(a => `<label><input type="checkbox" value="${a}" class="m_act"/> ${a}</label>`).join('')}
      </div>
    </div>
  `, async () => {
    const body = {
      username: document.getElementById('m_username').value.trim(),
      password: document.getElementById('m_pass').value,
      email: document.getElementById('m_email').value.trim(),
      full_name: document.getElementById('m_fullname').value.trim(),
      empresa: document.getElementById('m_empresa').value.trim(),
      role: document.getElementById('m_role').value,
      plan: document.getElementById('m_plan').value,
      activos_asignados: [...document.querySelectorAll('.m_act:checked')].map(c => c.value),
    };
    if (!body.username || !body.password) return toast('Usuario y contraseña requeridos', 'error');
    await api('/api/admin/users', { method: 'POST', body: JSON.stringify(body) });
    toast('Usuario creado con plan ' + body.plan, 'success');
    closeModal(); loadUsers();
  });
}

async function openEditUser(username) {
  const users = await api('/api/admin/users');
  const u = users.find(x => x.username === username);
  showModal('Editar ' + username, `
    <div class="form-row">
      <div class="form-group"><label>Email</label><input id="m_email" value="${u.email||''}"/></div>
      <div class="form-group"><label>Nombre</label><input id="m_fullname" value="${u.full_name||''}"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Empresa</label><input id="m_empresa" value="${u.empresa||''}"/></div>
      <div class="form-group"><label>Rol</label>
        <select id="m_role">
          <option value="viewer" ${u.role==='viewer'?'selected':''}>Viewer</option>
          <option value="operador" ${u.role==='operador'?'selected':''}>Operador</option>
          <option value="admin" ${u.role==='admin'?'selected':''}>Admin</option>
        </select>
      </div>
    </div>
    <div class="form-group"><label>Plan</label>
      <select id="m_plan">${planSelectHTML(u.plan || 'regional')}</select>
    </div>
    <div class="form-group"><label>Activos asignados</label>
      <div class="checkbox-grid">
        ${_activosCache.map(a => `<label><input type="checkbox" class="m_act" value="${a}" ${(u.activos_asignados||[]).includes(a)?'checked':''}/> ${a}</label>`).join('')}
      </div>
    </div>
  `, async () => {
    const body = {
      email: document.getElementById('m_email').value.trim(),
      full_name: document.getElementById('m_fullname').value.trim(),
      empresa: document.getElementById('m_empresa').value.trim(),
      role: document.getElementById('m_role').value,
      plan: document.getElementById('m_plan').value,
      activos_asignados: [...document.querySelectorAll('.m_act:checked')].map(c => c.value),
    };
    await api('/api/admin/users/' + encodeURIComponent(username), { method: 'PUT', body: JSON.stringify(body) });
    toast('Usuario actualizado', 'success'); closeModal(); loadUsers();
  });
}

function openResetPass(username) {
  showModal('Reset Contraseña — ' + username, `
    <div class="form-group"><label>Nueva contraseña (mín 8)</label><input id="m_newpass" type="password"/></div>
    <p style="color:var(--muted);font-size:12px;">El usuario deberá cambiarla en su próximo ingreso.</p>
  `, async () => {
    const np = document.getElementById('m_newpass').value;
    await api('/api/admin/users/' + encodeURIComponent(username) + '/reset-password',
              { method: 'POST', body: JSON.stringify({ new_password: np }) });
    toast('Contraseña reseteada', 'success'); closeModal();
  });
}

async function toggleUser(u) {
  if (!confirm(`Cambiar estado activo/inactivo de ${u}?`)) return;
  await api('/api/admin/users/' + encodeURIComponent(u) + '/toggle', { method: 'POST' });
  toast('Estado cambiado', 'success'); loadUsers();
}
async function deleteUser(u) {
  if (!confirm(`Eliminar usuario ${u}? Esta acción es definitiva.`)) return;
  await api('/api/admin/users/' + encodeURIComponent(u), { method: 'DELETE' });
  toast('Usuario eliminado', 'success'); loadUsers();
}

// ─── Plans ────────────────────────────────────────────────────────────────────
async function loadPlans() {
  try {
    const r = await api('/api/v55/plans');
    _plansCache = r.planes || [];
    document.getElementById('plansGrid').innerHTML = _plansCache.map(p => {
      const limites = p.limites || {};
      const features = Object.entries(limites).filter(([k,v]) => typeof v === 'boolean').map(([k,v]) => `
        <div style="font-size:12px;color:${v ? 'var(--green)' : 'var(--muted)'};padding:3px 0;">
          ${v ? '✓' : '○'} ${k.replace(/_/g, ' ')}
        </div>
      `).join('');
      return `
      <div class="card" style="border-top:4px solid ${p.color};margin:0;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <span style="font-size:28px;">${p.icon}</span>
          <div>
            <div style="font-size:18px;font-weight:800;color:${p.color};">${p.nombre}</div>
            <div style="font-size:13px;color:var(--muted);">${p.precio_mensual_usd_max ? '$' + p.precio_mensual_usd + '–' + p.precio_mensual_usd_max : '$' + p.precio_mensual_usd}/mes USD</div>
          </div>
        </div>
        <p style="font-size:13px;color:var(--text);margin-bottom:12px;">${p.publico_objetivo}</p>
        <div style="font-size:12px;margin-bottom:10px;">
          <div><b>Activos:</b> ${limites.max_activos === -1 ? 'Ilimitados' : limites.max_activos}</div>
          <div><b>Usuarios:</b> ${limites.max_usuarios === -1 ? 'Ilimitados' : limites.max_usuarios}</div>
          <div><b>Soporte:</b> ${limites.soporte_horas}h SLA</div>
        </div>
        <div style="border-top:1px solid var(--border);padding-top:10px;">
          ${features}
        </div>
      </div>`;
    }).join('');
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Tickets (admin) ──────────────────────────────────────────────────────────
async function loadAdminTickets() {
  try {
    const r = await api('/api/tickets?limit=300');
    const sum = r.resumen || {};
    document.getElementById('ticketsAdminContent').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card danger"><div class="stat-label">Élite P0</div><div class="stat-value">${sum.elite_p0 || 0}</div><div class="stat-sub">SLA 4h · Director Ops</div></div>
        <div class="stat-card warning"><div class="stat-label">Crítico P1</div><div class="stat-value">${sum.critico_p1 || 0}</div><div class="stat-sub">SLA 24h · Jefe HSE</div></div>
        <div class="stat-card"><div class="stat-label">Abiertos</div><div class="stat-value">${sum.abiertos || 0}</div></div>
        <div class="stat-card success"><div class="stat-label">Total</div><div class="stat-value">${r.total || 0}</div></div>
      </div>
      <div class="card">
        <div class="card-title">Tickets de Intervención</div>
        <div style="overflow-x:auto;">
          <table>
            <thead><tr><th>ID</th><th>Cat.</th><th>Activo</th><th>Operador</th><th>Score</th><th>SLA</th><th>Asignado</th><th>Estado</th></tr></thead>
            <tbody>
              ${(r.tickets || []).map(t => {
                const overdue = new Date(t.sla_deadline) < new Date() && t.estado === 'ABIERTO';
                return `<tr>
                  <td><code style="font-size:11px;color:var(--accent)">${t.ticket_id}</code></td>
                  <td><span class="pill ${t.categoria === 'ELITE' ? 'admin' : 'operador'}">${t.prioridad}</span></td>
                  <td><b>${t.activo}</b></td><td>${t.operador || '—'}</td>
                  <td><b style="color:${t.color}">${(t.score||0).toFixed(1)}</b></td>
                  <td style="color:${overdue ? 'var(--red)' : 'var(--muted)'};font-size:11px;">${overdue ? '⚠ VENCIDO' : t.sla_horas + 'h'}</td>
                  <td>${t.asignado_a || '<small style="color:var(--muted)">sin asignar</small>'}</td>
                  <td><span class="pill ${t.estado === 'ABIERTO' ? 'operador' : 'active'}">${t.estado}</span></td>
                </tr>`;
              }).join('') || '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:20px;">Sin tickets</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch(e) { toast(e.message, 'error'); }
}

// ─── Scheduler (admin) ────────────────────────────────────────────────────────
async function loadSchedulerStatus() {
  try {
    const s = await api('/api/scheduler/status');
    const next = s.next_run ? new Date(s.next_run) : null;
    const last = s.last_run ? new Date(s.last_run) : null;
    document.getElementById('schedulerContent').innerHTML = `
      <div class="stats-grid">
        <div class="stat-card ${s.running ? 'success' : 'danger'}"><div class="stat-label">Estado</div><div class="stat-value">${s.running ? '● ACTIVO' : '○ DETENIDO'}</div></div>
        <div class="stat-card"><div class="stat-label">Ejecuciones</div><div class="stat-value">${s.runs_total || 0}</div><div class="stat-sub">${s.errors_total || 0} errores</div></div>
        <div class="stat-card warning"><div class="stat-label">Próxima</div><div class="stat-value" style="font-size:14px;">${next ? next.toLocaleString('es-CO') : '—'}</div></div>
        <div class="stat-card success"><div class="stat-label">Última</div><div class="stat-value" style="font-size:14px;">${last ? last.toLocaleString('es-CO') : 'Aún no ejecutado'}</div></div>
      </div>
      <div class="card">
        <div class="card-title">Configuración del Pipeline Automático</div>
        <div style="font-size:13px;line-height:1.7;">
          <div><b>Schedule:</b> ${s.schedule}</div>
          <div><b>Alineación:</b> ${s.alineacion}</div>
          <div><b>Umbral CRÍTICO (P1):</b> Score ≥ ${s.umbral_ticket} → Ticket SLA 24h</div>
          <div><b>Umbral ÉLITE (P0):</b> Score ≥ ${s.umbral_elite} → Ticket SLA 4h escalado a Director Ops</div>
          <div style="margin-top:12px;padding:10px;background:var(--card2);border-left:3px solid var(--accent);border-radius:4px;font-size:12px;">
            <b>¿Qué hace el scheduler?</b><br/>
            Cada vez que arranca: descarga datos REALES de Sentinel-5P TROPOMI del día anterior,
            corre el pipeline (TROPOMI → meteo → ML → Supabase → Telegram → tickets auto).
            No requiere intervención manual.
          </div>
        </div>
      </div>`;
  } catch(e) { toast(e.message, 'error'); }
}

// ─── Audit Chain ──────────────────────────────────────────────────────────────
async function loadAudit() {
  try {
    const r = await api('/api/v55/audit/chain?limit=100');
    document.getElementById('auditBlocks').textContent = r.verificacion.total_bloques;
    document.getElementById('auditIntegrity').textContent = r.verificacion.integro ? '✓ ÍNTEGRA' : '✗ ROTA';
    document.getElementById('auditIntegrity').style.color = r.verificacion.integro ? 'var(--green)' : 'var(--red)';
    document.getElementById('auditLastHash').textContent = (r.verificacion.ultimo_hash || '').slice(0, 24) + '…';
    document.getElementById('auditTbody').innerHTML = r.bloques.map(b => `
      <tr><td>${b.index}</td><td><small>${fmtDate(b.timestamp)}</small></td>
        <td><b style="color:var(--accent)">${b.action}</b></td>
        <td>${b.actor}</td><td>${b.target}</td>
        <td><code style="font-size:10px;color:var(--green)">${(b.hash||'').slice(0,16)}…</code></td>
      </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px;">Sin eventos aún</td></tr>';
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Health ───────────────────────────────────────────────────────────────────
async function loadHealth() {
  try {
    const r = await api('/api/health');
    document.getElementById('healthDump').textContent = JSON.stringify(r, null, 2);
  } catch (e) { toast(e.message, 'error'); }
}

// ─── WebSocket Live ───────────────────────────────────────────────────────────
function startWebSocket() {
  try {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(proto + '//' + location.host + '/api/ws/live');
    ws.onopen = () => {
      document.getElementById('liveStatus').textContent = 'En vivo · datos reales';
    };
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      const log = document.getElementById('wsLog');
      const ts = new Date().toLocaleTimeString('es-CO');
      let line;
      if (data.type === 'pipeline.started') {
        line = `[${ts}] 🔄 PIPELINE INICIADO · descargando Sentinel-5P (${data.data?.date})`;
        toast('Pipeline ejecutándose con datos reales', 'success');
      } else if (data.type === 'pipeline.completed') {
        const d = data.data || {};
        line = `[${ts}] ✓ PIPELINE OK · ${d.total_detecciones} detecciones · ${d.alertas_elite} élite · $${(d.perdida_usd_dia||0).toFixed(0)}/día · fuente=${d.fuente}`;
        toast(`Pipeline completado: ${d.total_detecciones} detecciones reales`, 'success');
        loadDashboard();
        refreshTicketsBadge();
      } else if (data.type === 'detection.elite') {
        const d = data.data || {};
        line = `[${ts}] 🚨 ELITE: ${d.activo} score=${(d.score||0).toFixed(1)} ${(d.ch4_ppb||0).toFixed(0)}ppb`;
      } else if (data.type === 'ticket.created') {
        const d = data.data || {};
        line = `[${ts}] 🎫 TICKET ${d.prioridad}: ${d.activo} score=${(d.score||0).toFixed(1)} SLA=${d.sla_horas}h`;
        toast(`Nuevo ticket ${d.prioridad}: ${d.activo}`, d.categoria === 'ELITE' ? 'error' : 'success');
        refreshTicketsBadge();
      } else if (data.type === 'pipeline.error') {
        line = `[${ts}] ⚠ ERROR: ${data.data?.error}`;
        toast('Error en pipeline: ' + data.data?.error, 'error');
      } else {
        line = `[${ts}] ${data.type}: status=${data.system_status} pipeline=${data.pipeline_running}`;
      }
      if (log) {
        log.textContent = line + '\n' + log.textContent;
        if (log.textContent.length > 12000) log.textContent = log.textContent.slice(0, 12000);
      }
    };
    ws.onclose = () => {
      document.getElementById('liveStatus').textContent = 'Reconectando…';
      setTimeout(startWebSocket, 5000);
    };
    ws.onerror = () => {};
  } catch (e) {}
}

// ─── Modal ────────────────────────────────────────────────────────────────────
function showModal(title, body, onConfirm) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').innerHTML = body;
  document.getElementById('modal').classList.add('active');
  document.getElementById('modalConfirm').onclick = async () => {
    try { await onConfirm(); } catch (e) { toast(e.message, 'error'); }
  };
}
function closeModal() {
  document.getElementById('modal').classList.remove('active');
}

document.addEventListener('DOMContentLoaded', init);
