# MetanoSRGAN Elite v5.5 — Mata-Gigantes Edition

> Sistema de Detección de Metano por Satélite con IA — 24/7 — Magdalena Medio, Colombia

[![Render](https://img.shields.io/badge/Deploy-Render-46e3b7)](https://render.com)
[![Sentinel-5P](https://img.shields.io/badge/Data-Sentinel--5P-0070d6)](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-5p)
[![Supabase](https://img.shields.io/badge/DB-Supabase-3ecf8e)](https://supabase.com)
[![Mapbox](https://img.shields.io/badge/Map-Mapbox%20GL-000)](https://www.mapbox.com)

## ⚡ Lo nuevo en v5.5

| 🆕 | Descripción |
|----|-------------|
| 🛡 **Panel Admin Completo** | CRUD usuarios, roles, asignación de activos, audit log inmutable |
| 🌱 **Créditos de Carbono** | Verra VM0033 + Gold Standard + EU ETS (IPCC AR6 GWP=29.8) |
| 📋 **Compliance** | EPA OOOOa/b · EU MRR · RUA-PI Colombia · OGMP 2.0 · WB GMFR |
| 📤 **Exportadores** | PDF ejecutivo · Excel multihoja · CSV |
| 🔑 **API Keys públicas** | Sistema con scopes y rate-limit para integradores |
| 🔔 **Webhooks salientes** | SCADA · Slack · MS Teams · ERP — con HMAC-SHA256 |
| ⛓ **Audit Chain** | SHA-256 encadenado tipo blockchain para inmutabilidad |
| 📊 **Analytics** | Comparativas día/semana/mes/año + ranking de activos |
| 🔴 **WebSocket Live** | Heartbeat cada 5 s al panel admin |
| 📧 **Login por email** | `ortizisacc18@gmail.com` o usuario plano |

## 🚀 Despliegue

Ver `DEPLOYMENT_MANUS.md` para guía completa paso a paso.

```bash
# 1. Configura .env basado en .env.example
cp .env.example .env

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Local
uvicorn server:app --host 0.0.0.0 --port 8000

# 4. Render → ver render.yaml
```

## 🔐 Credenciales Admin

⚠️ Las credenciales del administrador principal NO se publican en repositorios públicos.
Solicítalas al equipo de operaciones o consulta el archivo privado `memory/test_credentials.md` (no commiteado a producción).

## 📡 Datos Reales en Vivo

- ✅ Copernicus Sentinel-5P TROPOMI
- ✅ Open-Meteo (viento, CH4 ambiental)
- ✅ Supabase PostgreSQL Cloud (409+ detecciones)
- ✅ Mapbox GL JS v3
- ✅ Telegram Bot (@MetanoAlerts_bot)
- ✅ scikit-learn ML (RandomForest pre-entrenado)

## 📚 Documentación

- API Docs: `/api/docs` (Swagger)
- ReDoc: `/api/redoc`
- v5.5 Info: `/api/v55/info`

---

*MetanoSRGAN Elite v5.5 — 2026 — Diseñado para operar 24/7 en producción*
