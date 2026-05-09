# 🏗️ ARQUITECTURA TÉCNICA - MetanoSRGAN Elite v2.1

**Proyecto:** METAvision (Dashboard de Inteligencia Geoespacial del Metano)
**Stack:** FastAPI + React + MongoDB + WebSocket
**Fecha:** 20 de abril de 2026

---

## 📐 DIAGRAMA DE ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO (Browser)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    HTTP + WebSocket
                         │
        ┌────────────────┴────────────────┐
        │                                 │
    ┌───▼────────────────────┐    ┌──────▼──────────────────┐
    │   FRONTEND (React)     │    │  WebSocket Client       │
    │  ├─ Pages/            │    │  ├─ Real-time alerts    │
    │  ├─ Components/       │    │  ├─ Live updates        │
    │  ├─ Auth Context      │    │  └─ Status streaming    │
    │  └─ API Client        │    │                         │
    └───┬────────────────────┘    └──────┬──────────────────┘
        │                                 │
        └────────────────┬────────────────┘
                    REST API
                         │
        ┌────────────────▼────────────────┐
        │   BACKEND (FastAPI)             │
        │  ├─ Routes (10+ endpoints)      │
        │  ├─ Auth (JWT + bcrypt)         │
        │  ├─ WebSocket Manager           │
        │  ├─ Services (simulador, etc)   │
        │  └─ Middleware (CORS, logging)  │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
    ┌───▼──────────────────┐    ┌────────▼─────────────┐
    │  MongoDB (Motor)     │    │  External APIs       │
    │  ├─ Detections       │    │  ├─ Copernicus       │
    │  ├─ Alerts           │    │  ├─ Weather          │
    │  ├─ Stations         │    │  └─ Other services   │
    │  ├─ Users            │    │                      │
    │  └─ Reports          │    │                      │
    └──────────────────────┘    └──────────────────────┘
```

---

## 🔌 ENDPOINTS API

### Autenticación
```
POST   /api/auth/login              → JWT token
GET    /api/auth/me                 → Current user
POST   /api/auth/logout             → Invalidate token
```

### Datos Geoespaciales
```
GET    /api/stations                → Lista de estaciones
GET    /api/stations/{id}           → Detalles de estación
GET    /api/wells?bbox=&status=     → Pozos de petróleo
GET    /api/wells/{id}              → Detalles de pozo
GET    /api/pipelines?bbox=         → Tuberías
GET    /api/pipelines/{id}          → Detalles de tubería
```

### Detecciones y Alertas
```
GET    /api/detections?...          → Filtrar detecciones
GET    /api/detections/{id}         → Detalles de detección
PATCH  /api/detections/{id}         → Actualizar estado
POST   /api/detections              → Crear detección (admin)

GET    /api/alerts?...              → Filtrar alertas
GET    /api/alerts/{id}             → Detalles de alerta
POST   /api/alerts/{id}/ack         → Reconocer alerta
```

### Datos Ambientales
```
GET    /api/wind?at=ISO             → Datos de viento
GET    /api/stats/overview          → Estadísticas generales
```

### Inferencia y Reportes
```
POST   /api/inference/jobs          → Crear job de inferencia
GET    /api/inference/jobs          → Listar jobs
GET    /api/inference/jobs/{id}     → Estado del job
GET    /api/model/info              → Información del modelo

POST   /api/reports                 → Generar reporte
GET    /api/reports                 → Listar reportes
GET    /api/reports/{id}            → Detalles del reporte
GET    /api/reports/{id}/download   → Descargar PDF/CSV
```

### WebSocket
```
WS     /api/ws/alerts?token=JWT     → Stream de alertas en vivo
```

---

## 🗄️ ESQUEMA DE BASE DE DATOS (MongoDB)

### Colección: users
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password_hash": "bcrypt_hash",
  "role": "admin|analyst|viewer",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### Colección: stations
```json
{
  "_id": ObjectId,
  "name": "Vasconia",
  "location": {
    "type": "Point",
    "coordinates": [-74.472, 5.922]
  },
  "type": "compression|monitoring",
  "status": "active|inactive",
  "metadata": {}
}
```

### Colección: detections
```json
{
  "_id": ObjectId,
  "detected_at": ISODate,
  "location": {
    "type": "Point",
    "coordinates": [lng, lat]
  },
  "concentration_ppb": 2210.5,
  "confidence": 0.94,
  "severity": "critical|warning|normal",
  "source_station_id": ObjectId,
  "status": "new|acknowledged|resolved",
  "created_by": ObjectId
}
```

### Colección: alerts
```json
{
  "_id": ObjectId,
  "detection_id": ObjectId,
  "type": "CRÍTICA|PREVENTIVA|NORMAL",
  "message": "Alert description",
  "acknowledged_at": ISODate,
  "acknowledged_by": ObjectId,
  "created_at": ISODate
}
```

### Colección: reports
```json
{
  "_id": ObjectId,
  "title": "Report title",
  "type": "pdf|csv",
  "filters": { "start_date": ISODate, "end_date": ISODate },
  "status": "pending|completed|failed",
  "file_path": "storage/reports/...",
  "created_by": ObjectId,
  "created_at": ISODate
}
```

---

## 🔐 AUTENTICACIÓN Y AUTORIZACIÓN

### Flujo JWT
```
1. Usuario envía email + password → POST /api/auth/login
2. Backend valida contra MongoDB
3. Backend genera JWT (HS256, 12 horas)
4. Frontend almacena JWT en localStorage
5. Cada request incluye: Authorization: Bearer <JWT>
6. Backend valida JWT en cada endpoint
```

### Roles y Permisos
| Rol | Permisos |
| :--- | :--- |
| **admin** | CRUD completo, crear jobs, resetear seed |
| **analyst** | Crear detecciones, reconocer alertas, generar reportes |
| **viewer** | Solo lectura de todas las vistas |

---

## 🔄 FLUJO DE DATOS EN TIEMPO REAL

### Simulador de Alertas
```
1. Backend inicia con SIMULATE_ALERTS=true
2. Cada 45-90 segundos:
   - Genera detección sintética en Magdalena Medio
   - Crea alerta asociada
   - Guarda en MongoDB
   - Emite via WebSocket a clientes conectados
3. Frontend recibe via WebSocket
4. UI actualiza en tiempo real (sin refresh)
```

### WebSocket Connection
```
1. Frontend: ws://backend:8000/api/ws/alerts?token=JWT
2. Backend: ConnectionManager mantiene lista de clientes
3. Cuando hay nueva alerta:
   - Backend itera sobre clientes conectados
   - Envía JSON con detalles de alerta
4. Frontend recibe y actualiza estado React
```

---

## 📦 DEPENDENCIAS PRINCIPALES

### Backend
```
fastapi==0.104.1
motor==3.3.2 (async MongoDB)
pydantic==2.5.0
python-jose==3.3.0 (JWT)
passlib==1.7.4 (bcrypt)
shapely==2.0.1 (geometría)
python-multipart==0.0.6
```

### Frontend
```
react==18.2.0
react-router-dom==6.20.0
tailwindcss==3.3.0
shadcn/ui (componentes)
axios==1.6.0 (HTTP client)
zustand==4.4.0 (state management)
```

---

## 🚀 DESPLIEGUE

### Desarrollo Local
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py

# Frontend (en otra terminal)
cd frontend
yarn install
yarn start
```

### Producción (Docker)
```dockerfile
# Backend
FROM python:3.11
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "server.py"]

# Frontend
FROM node:18
WORKDIR /app
COPY frontend/package.json .
RUN yarn install
COPY frontend/ .
RUN yarn build
CMD ["yarn", "serve"]
```

---

## 🧪 TESTING

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Smoke Tests (Validación Fase 1)
```bash
bash scripts/smoke_phase1.sh
```

### Manual Testing
- Ver `auth_testing.md` para flujos de autenticación
- Ver `test_result.md` para resultados anteriores

---

## 🔗 INTEGRACIÓN CON MetanoSRGAN Elite

### Modelo ONNX (Pendiente)
```
1. Exportar best.pt → metano_srgan_elite.onnx
2. Cargar en backend: onnxruntime.InferenceSession()
3. Endpoint: POST /api/inference/jobs
4. Input: Sentinel-5P NRTI (7km)
5. Output: Super-resolución (10m) + detecciones
```

### Datos Sentinel (Pendiente)
```
1. Conectar Copernicus Data Space API
2. Descargar Sentinel-2 (10m) y Sentinel-5P (7km)
3. Procesar y alinear
4. Ejecutar modelo SRGAN
5. Guardar detecciones en MongoDB
```

---

## 📊 MONITOREO Y LOGGING

### Logs del Backend
```
[2026-04-20 15:30:45] INFO: Server started on 0.0.0.0:8000
[2026-04-20 15:30:50] INFO: User admin logged in
[2026-04-20 15:31:00] INFO: New detection created (confidence: 0.94)
[2026-04-20 15:31:05] INFO: Alert emitted to 3 connected clients
```

### Métricas Clave
- Requests por segundo
- Latencia de API
- Conexiones WebSocket activas
- Detecciones generadas por hora
- Tasa de error

---

## ⚙️ VARIABLES DE ENTORNO

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=metano_srgan
CORS_ORIGINS=http://localhost:3000
JWT_SECRET=your-secret-key
JWT_ALG=HS256
JWT_EXPIRES_HOURS=12
AUTH_PROVIDER=local
SIMULATE_ALERTS=true
SIM_MIN_S=45
SIM_MAX_S=90
LOG_LEVEL=INFO
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_MAPBOX_TOKEN=pk_test_...
REACT_APP_AUTH_PROVIDER=local
```

---

*Documento técnico de referencia para desarrolladores*
*Última actualización: 20 de abril de 2026*
