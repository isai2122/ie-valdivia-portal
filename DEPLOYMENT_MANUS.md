# MetanoSRGAN Elite v5.5 — Guía de Despliegue para Manus / Render

> Sistema de Detección de Metano 24/7 — Magdalena Medio, Colombia  
> Datos reales: Copernicus Sentinel-5P TROPOMI + Open-Meteo + Supabase  
> v5.5 "Mata-Gigantes Edition" — Panel Admin Completo, Compliance, Créditos de Carbono, API Keys, Webhooks

---

## 0. Resumen de cambios v5.4 → v5.5

| Categoría | Cambio |
|-----------|--------|
| **🔧 Bugs corregidos** | `return token_data` (7 endpoints), `verify_token` tuple unpacking, `auth_manager.login()`, `revoke_token` → `logout()` |
| **🔐 Login** | Soporta usuario o **email** (`ortizisacc18@gmail.com`) |
| **👑 Admin Principal** | `ortizisacc18@gmail.com` / `212228IsaiJosias@` (sincronizado en cada arranque) |
| **🆕 Panel Admin** | `/admin` con CRUD usuarios, roles, activos, audit log, health monitor, etc. |
| **🌱 Créditos de Carbono** | Verra VM0033 + Gold Standard + EU ETS + CARB (IPCC AR6 GWP=29.8) |
| **📋 Compliance** | EPA OOOOa/b · EU MRR 2024/1787 · RUA-PI Colombia · OGMP 2.0 · WB GMFR |
| **📤 Exportadores** | PDF (reportlab) · Excel (openpyxl, multi-hoja) · CSV |
| **🔑 API Keys** | Sistema público con scopes y rate limit |
| **🔔 Webhooks** | Salientes a SCADA/Slack/Teams/ERP con HMAC-SHA256 |
| **⛓ Audit Chain** | Cadena tipo blockchain con SHA-256 encadenado |
| **📊 Analytics** | Comparativas por día/semana/mes/año + ranking de activos |
| **🔴 WebSocket Live** | `/api/ws/live` push de heartbeat cada 5 s |

---

## 1. Estructura del repositorio

```
/
├── server.py                  ← Entry point para Render (uvicorn server:app)
├── Procfile                   ← web: uvicorn server:app
├── render.yaml                ← Configuración multi-servicio para Render
├── requirements.txt           ← Dependencias Python
├── .env.example               ← Plantilla de variables de entorno
├── backend/
│   ├── server.py              ← FastAPI app canónica (importada por root server.py)
│   ├── enhancements_v55.py    ← 🆕 Carbon, Compliance, Exports, API Keys, Webhooks, Audit Chain
│   ├── admin_panel_v54.py
│   ├── jwt_auth_v36.py
│   ├── supabase_integration_v38.py
│   ├── tropomi_direct_v37.py
│   ├── ml_persistence_v37.py
│   ├── detection_pipeline_v35.py
│   ├── telegram_notifier_v39.py
│   └── … (otros módulos v3.x preservados)
├── frontend/
│   ├── index.html             ← Dashboard público (intacto + botón Admin)
│   ├── login.html             ← 🆕 Pantalla de login
│   ├── admin.html             ← 🆕 Panel Admin v5.5
│   ├── admin.js               ← 🆕 Lógica del panel admin
│   ├── static-server.js       ← Servidor estático Node (sólo dev local)
│   └── package.json           ← Dependencias (vacío en prod)
├── data/
│   ├── event_master_table.json (409 eventos reales)
│   └── IA_STATUS_24_7.json
└── telegram_bot/
    └── metano_alerts_bot_v40.py
```

> En **Render**, sólo se usa el `server.py` raíz, que sirve **TODO** (API + frontend estático). El servidor Node `static-server.js` es únicamente para entorno local de desarrollo.

---

## 2. Variables de entorno requeridas en Render

Configura estas variables en **Render Dashboard → Service → Environment**:

| Variable | Obligatoria | Valor recomendado / Cómo obtenerla |
|----------|-------------|-------------------------------------|
| `SUPABASE_URL` | ✅ | https://mfkzozkfggbmcjouiepk.supabase.co (o tu instancia) |
| `SUPABASE_ANON_KEY` | ✅ | Supabase Dashboard → Settings → API → anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase Dashboard → Settings → API → service_role key |
| `MAPBOX_TOKEN` | ✅ | https://account.mapbox.com/access-tokens (token público pk.*) |
| `TELEGRAM_BOT_TOKEN` | Opcional | @BotFather en Telegram → /newbot |
| `JWT_SECRET_KEY` | ✅ | **Genera uno nuevo seguro** (mínimo 32 chars aleatorios) |
| `JWT_EXPIRE_MINUTES` | Opcional | `60` (default) |
| `JWT_REFRESH_DAYS` | Opcional | `7` (default) |
| `ADMIN_USERNAME` | Opcional | `admin` (default — usuario fallback) |
| `ADMIN_PASSWORD` | Opcional | Contraseña del fallback `admin` (no del admin principal) |
| `BREVO_API_KEY` | Opcional | Solo si usas correos transaccionales |
| `ELITE_SCORE_THRESHOLD` | Opcional | `50` |
| `SIMULATE_ALERTS` | Opcional | `false` (PRODUCCIÓN) |

> **Admin principal `ortizisacc18@gmail.com`** se crea automáticamente al arranque con la contraseña hard-coded del usuario (`212228IsaiJosias@`). NO se requiere variable de entorno para esto.

### Generar `JWT_SECRET_KEY` seguro

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 3. Pasos para desplegar (Manus)

### Opción A — Despliegue mediante `render.yaml` (recomendado)

1. **Sube el repo a GitHub** (sin commitear `.env` real, sólo `.env.example`).
2. En Render Dashboard, **New + → Blueprint**.
3. Conecta el repo. Render detectará `render.yaml` y creará 2 servicios:
   - `metanosrgan-elite-v55` (web)
   - `metanosrgan-telegram-bot` (worker, opcional)
4. Render solicitará rellenar las variables marcadas con `sync: false`. Pega los valores de la tabla anterior.
5. Click **Apply**.
6. Espera ~3-5 min al primer build. Cuando el health check `/api/health` pase, el servicio quedará **Live**.

### Opción B — Servicio único manual

1. **New + → Web Service**.
2. Repositorio + branch `main`.
3. **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
4. **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT --workers 1`
5. **Health Check Path**: `/api/health`
6. Pega las variables de entorno.
7. **Create Web Service**.

---

## 4. Verificación post-despliegue

Reemplaza `https://TU-APP.onrender.com` por la URL real:

```bash
# 1. Health check
curl https://TU-APP.onrender.com/api/health

# 2. Login con admin principal
curl -X POST https://TU-APP.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ortizisacc18@gmail.com","password":"212228IsaiJosias@"}'

# 3. Panel admin (web)
open https://TU-APP.onrender.com/admin

# 4. API docs
open https://TU-APP.onrender.com/api/docs

# 5. Resumen v5.5
curl https://TU-APP.onrender.com/api/v55/info
```

---

## 5. Endpoints v5.5 nuevos (todos disponibles tras login admin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v55/info` | Info de capacidades v5.5 |
| GET | `/api/v55/carbon/credits` | Cálculo de créditos por detección |
| GET | `/api/v55/carbon/constants` | GWP IPCC + precios mercado carbono |
| GET | `/api/v55/compliance/normativas` | Lista de normativas evaluadas |
| GET | `/api/v55/compliance/summary` | Resumen de cumplimiento global |
| GET | `/api/v55/compliance/violations` | Detecciones que exceden normativa |
| GET | `/api/v55/export/{csv,excel,pdf}` | Descargar reportes |
| GET/POST/DELETE | `/api/v55/keys` | Gestión de API Keys |
| GET/POST/DELETE | `/api/v55/webhooks` | Gestión de Webhooks |
| POST | `/api/v55/webhooks/{id}/test` | Ping de prueba a webhook |
| GET | `/api/v55/audit/chain` | Cadena hash inmutable |
| GET | `/api/v55/analytics/by-period?kind=month` | Comparativas |
| GET | `/api/v55/analytics/by-asset` | Ranking de activos |
| WS  | `/api/ws/live` | WebSocket de heartbeat |

---

## 6. Acceso al Panel Admin

1. Ir a `https://TU-APP.onrender.com/login`
2. **Usuario o email**: `ortizisacc18@gmail.com`
3. **Contraseña**: `212228IsaiJosias@`
4. Al ingresar, te redirige a `/admin` con todas las secciones disponibles.

> Si pierdes la contraseña, se restablece automáticamente en cada reinicio del servicio (al startup).

---

## 7. Datos reales en vivo

El sistema **ya está conectado a fuentes reales**:

- ✅ **Supabase PostgreSQL** (cloud) — 409+ detecciones almacenadas
- ✅ **Copernicus Sentinel-5P TROPOMI** vía API directa de Copernicus Data Space
- ✅ **Open-Meteo** para viento y CH4 ambiental
- ✅ **CAMS (Copernicus Atmosphere Monitoring Service)** como fallback
- ✅ **Mapbox GL JS v3** para mapa satelital interactivo
- ✅ **Telegram Bot** real para alertas push (@MetanoAlerts_bot)
- ✅ **ML scikit-learn** RandomForest pre-entrenado con histórico

---

## 8. Notas para Render Free Tier

- El plan **Free** se duerme tras 15 min de inactividad. Para producción 24/7, usa **Starter ($7/mes)**.
- En `render.yaml` ya está configurado `plan: starter` para evitar dormancia.
- El bot de Telegram (`metanosrgan-telegram-bot`) es un **Worker**, NO se duerme.

---

## 9. Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'reportlab'` | Re-deploy: `pip install -r requirements.txt` |
| Frontend no carga (404 en `/`) | Verifica que `frontend/index.html` esté en el repo |
| Login falla con 401 | Verifica `JWT_SECRET_KEY` en env vars de Render |
| Supabase no conecta | Verifica `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` |
| Bot Telegram no responde | Configura `WEBHOOK_URL=https://TU-APP.onrender.com` |
| Mapbox no muestra mapa | Verifica `MAPBOX_TOKEN` en env vars |

---

## 10. Próximas mejoras sugeridas (v5.6+)

- [ ] PWA / Service Worker para uso offline en campo
- [ ] Multi-idioma (i18n) ES/EN/PT
- [ ] Integración con SAP S/4HANA (módulo EHS)
- [ ] Alertas SMS vía Twilio
- [ ] Comparación visual antes/después con SRGAN
- [ ] Marketplace de créditos de carbono on-chain (Polygon)
- [ ] Modelo OGMP 2.0 Gold tier completo
- [ ] Dashboard regulatorio embebible (iframe para ANLA / EPA)

---

**🔐 Credenciales del Admin Principal**

| Campo | Valor |
|-------|-------|
| Email/Usuario | `ortizisacc18@gmail.com` |
| Contraseña | `212228IsaiJosias@` |
| Rol | `admin` (control total) |
| URL Panel | `https://TU-APP.onrender.com/admin` |

---

*MetanoSRGAN Elite v5.5 — Mata-Gigantes Edition · 2026*
