# METAvision — Dashboard de Inteligencia Geoespacial del Metano

Aplicación web **FARM** (FastAPI + React + MongoDB) para visualizar, analizar y
gestionar detecciones de fugas de metano sobre el Magdalena Medio, Colombia.

- **Producto:** METAvision
- **Motor de IA interno:** MetanoSRGAN Elite v2.1 (PSNR 32.19 dB)
- **Fase actual:** Fase 1 — backend core, WebSocket y seeders realistas

## Arquitectura

```
/app/
├── backend/                FastAPI + Motor (async Mongo) + JWT + WS
│   ├── server.py
│   ├── app/
│   │   ├── core/           config, security (JWT/bcrypt), logging, middleware
│   │   ├── auth/           AuthProvider (local JWT / Firebase stub) + deps
│   │   ├── db/             motor client + seed (idempotente, CLI --reset)
│   │   ├── models/         Pydantic v2
│   │   ├── routes/         REST bajo /api
│   │   ├── services/       simulator, plume (shapely)
│   │   └── ws/             ConnectionManager + /api/ws/alerts
│   └── storage/            inference/, reports/
├── frontend/               CRA + React + Tailwind v3 + shadcn/ui + yarn
└── scripts/
    ├── smoke.sh            baseline Fase 0
    └── smoke_phase1.sh     cubre criterios 1..12 de Fase 1
```

## Endpoints clave (`/api/docs` para la lista completa)

| Recurso      | Rutas |
|--------------|-------|
| auth         | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| stations     | `GET /stations`, `GET /stations/{id}` |
| wells        | `GET /wells?bbox=&status=&type=`, `GET /wells/{id}` |
| pipelines    | `GET /pipelines?bbox=&status=`, `GET /pipelines/{id}` |
| detections   | `GET /detections?bbox=&start_date=&end_date=&severity=&status=&min_confidence=`, `GET /detections/{id}`, `PATCH /detections/{id}` (analyst+admin), `POST /detections` (admin) |
| wind         | `GET /wind?at=ISO` |
| alerts       | `GET /alerts?...`, `GET /alerts/{id}`, `POST /alerts/{id}/ack` (analyst+admin) |
| inference    | `POST /inference/jobs` (analyst+admin), `GET /inference/jobs`, `GET /inference/jobs/{id}`, `GET /model/info` |
| reports      | `POST /reports`, `GET /reports`, `GET /reports/{id}`, `GET /reports/{id}/download` |
| stats        | `GET /stats/overview` |
| ws           | `WS /api/ws/alerts?token=<JWT>` |

## Variables de entorno

Backend (`/app/backend/.env`):
```
MONGO_URL, DB_NAME, CORS_ORIGINS
JWT_SECRET, JWT_ALG=HS256, JWT_EXPIRES_HOURS=12
AUTH_PROVIDER=local|firebase
SIMULATE_ALERTS=true|false, SIM_MIN_S, SIM_MAX_S
```

Frontend (`/app/frontend/.env`):
```
REACT_APP_BACKEND_URL
REACT_APP_MAPBOX_TOKEN
REACT_APP_AUTH_PROVIDER=local|firebase
```

## Comandos útiles

```bash
# Smoke tests
bash /app/scripts/smoke_phase1.sh

# Reseed completo (drop colecciones excepto users; idempotente al reiniciar)
cd /app/backend && python -m app.db.seed --reset

# Restart
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

## Credenciales demo

Ver `/app/memory/test_credentials.md`. Roles: `admin`, `analyst`, `viewer`.

## Lo que está simulado/mock (declarado)

- **`POST /api/inference/jobs`** usa `runner="demo-synthetic"`. Genera 1-3 detecciones sintéticas en el bbox del Magdalena Medio; **no ejecuta el modelo ONNX**. La respuesta incluye un `warning` explícito. La inferencia real quedará disponible cuando se exporte `metano_srgan_elite.onnx` desde el notebook v2.1.
- **Simulador de alertas** (`SIMULATE_ALERTS=true`) inyecta una detección + alerta cada 45-90s mientras el backend está arriba.
- **Reports PDF**: responden 501 hasta Fase 5. CSV sí funciona (pandas).
- **Seed de detecciones/alerts/wind samples**: valores sintéticos verosímiles, no datos reales de Sentinel-5P.
