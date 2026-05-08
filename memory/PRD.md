# MetanoSRGAN Elite v5.5 — PRD (Producción)

## Problema original
Sistema de detección de metano por satélite ya en Render. Mantener funcionalidad intacta + agregar mejoras "para superar grandes empresas" + admin que solo gestiona usuarios + sistema de planes ($800 / $2500 / $8000) + datos 100% reales en vivo + auth-first + nivel enterprise estricto + listo para que Manus suba a Render.

## Decisiones arquitectónicas finales
- **Auth-first**: `/` redirige a `/login`. Sin sesión = no se ve nada.
- **Roles**: admin (gestiona usuarios/planes), viewer/operador (consume features según plan)
- **3 Planes**: Regional ($800), Operacional ($2500), Enterprise ($8000–15000)
- **Feature gating**: cada endpoint v5.5 valida el plan del usuario antes de responder
- **Datos REALES**: Supabase (409 detecciones), Sentinel-5P TROPOMI Copernicus, Open-Meteo CH4 + viento, Mapbox satellite-streets-v12 (≈1m), Telegram bot, ML RandomForest entrenado con datos reales
- **Sin datos simulados**: `/api/system/diagnostics` lo verifica y reporta `datos_simulados: false`
- **WebSocket**: broadcastea eventos REALES del pipeline (started, completed, detection.elite, error)

## Implementado v5.5

### Backend
- `enhancements_v55.py`: CarbonCreditCalculator (IPCC AR6 GWP=29.8 + Verra/Gold/EU ETS), ComplianceTracker (5 normativas), Exporter (PDF/Excel/CSV), ApiKeyManager, WebhookManager (HMAC-SHA256), AuditChain (SHA-256 encadenado), HistoricalAnalytics
- `plans_v55.py`: 3 planes con feature matrix completa, gating por endpoint via `require_feature()`
- `/api/system/diagnostics`: verifica EN VIVO Supabase, TROPOMI, Open-Meteo, Mapbox, Telegram, ML, JWT, EOX tiles, pipeline
- `/api/v55/satellite/layers`: devuelve URLs y disponibilidad de capas (Sentinel-1 SAR, Sentinel-2 SWIR, EOX cloudless) según plan
- WebSocket `/api/ws/live` con `_broadcast_event()` que push eventos reales

### Frontend
- `/login`: sin placeholder de credenciales (solo `usuario@empresa.com`)
- `/admin`: panel reducido a 5 secciones (Dashboard, Usuarios, Planes, Auditoría, Salud Sistema). Botón "Ejecutar pipeline ahora". Soporta plan + empresa al crear usuario.
- `/app`: dashboard de USUARIO con feature gating visual (🔒 en pestañas no incluidas), Mapbox satellite-streets-v12, capas Sentinel toggle (locked si plan no incluye), auto-refresh 60s, botón "Actualizar datos", indicadores en vivo de Supabase/Sentinel-5P/Open-Meteo/Salud
- Responsive mobile con hamburger menu, tabs scrollables, viewports 480/768/1920 testeados

### Bugs corregidos
- 8 bugs de iteración 1 (return token_data, verify_token tuple, refresh_token, login)
- `/api/ml/predictions` (iteration 1 fix incompleto): coerción defensiva `_f()` + datetime tz-aware unification

## Testing final
- **Backend**: 100% en suite v5.5 (20/20). Combinado con iter1: 55/55.
- **Frontend**: 100% en 7 flujos e2e (auth-first, login hygiene, regional → /app, plan pill, mapa Mapbox real con marcadores, mobile responsive con 🔒, admin → /admin con 5 secciones)
- **Datos**: 409 detecciones reales Supabase, CH4 1411 ppb actual Open-Meteo, ML entrenado con 449 eventos

## Credenciales (privadas — NO publicar)
- Admin: `ortizisacc18@gmail.com / 212228IsaiJosias@`
- Test regional: `jr@ecopetrol.com / Ecopetrol2026!`
- Test enterprise: `enterprise@ecopetrol.com / Enterprise2026!`

## Despliegue Render
- `render.yaml`: web (uvicorn server:app) + worker (telegram bot)
- Variables env documentadas en `DEPLOYMENT_MANUS.md`
- Procfile + requirements.txt + .env.example listos

## Backlog futuro
- P1: SMS Twilio, Stripe self-subscription, Multi-idioma ES/EN/PT
- P2: PWA offline, Marketplace créditos on-chain (Polygon), SAP S/4HANA EHS
- P3: Cobertura mundial, SRGAN propio, MongoDB Atlas migration (si se solicita)

---
*Última actualización: 2026-05-08 · v5.5.0 "Mata-Gigantes Edition"*
