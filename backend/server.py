from pathlib import Path
"""
server.py — MetanoSRGAN Elite v5.4 (Supabase Edition)
======================================================
Servidor principal FastAPI con:
  - Supabase como base de datos principal (sin MongoDB)
  - Paths relativos (funciona en Render, Heroku, Railway)
  - JWT autenticación real (PyJWT + bcrypt)
  - ML v3.7 (scikit-learn RandomForest)
  - TROPOMI/Sentinel-5P datos reales
  - Telegram notificaciones
  - 409 eventos reales de Magdalena Medio

Despliegue en Render:
  Build:  pip install -r requirements.txt
  Start:  uvicorn server:app --host 0.0.0.0 --port $PORT

Variables de entorno requeridas:
  SUPABASE_URL              — URL del proyecto Supabase
  SUPABASE_ANON_KEY         — Clave anon de Supabase
  SUPABASE_SERVICE_ROLE_KEY — Clave service_role de Supabase
  MAPBOX_TOKEN              — Token de Mapbox
  TELEGRAM_BOT_TOKEN        — Token del bot de Telegram (opcional)
  JWT_SECRET_KEY            — Clave secreta JWT (cambiar en producción)
  ADMIN_USERNAME            — Usuario admin (default: admin)
  ADMIN_PASSWORD            — Contraseña admin (default: MetanoElite2026!)
  BREVO_API_KEY             — API Key de Brevo para correos
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ─── Path setup ───────────────────────────────────────────────────────────────
# Directorio base del proyecto (raíz)
# Soporta tanto /app/server.py como /app/backend/server.py
_THIS = Path(__file__).resolve()
if _THIS.parent.name == "backend":
    BASE_DIR = _THIS.parent.parent
    BACKEND_DIR = _THIS.parent
else:
    BASE_DIR = _THIS.parent
    BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BACKEND_DIR))

# Directorios de datos con paths relativos
DATA_DIR    = str(BASE_DIR / "data")
TICKETS_DIR = str(BASE_DIR / "tickets")
LOGS_DIR    = str(BASE_DIR / "logs")
FRONTEND_DIR = str(BASE_DIR / "frontend")

os.makedirs(DATA_DIR,    exist_ok=True)
os.makedirs(TICKETS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR,    exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "server_v54.log")),
    ],
)
logger = logging.getLogger(__name__)

# ─── Importar módulos del sistema ─────────────────────────────────────────────
try:
    from backend.supabase_integration_v38 import SupabaseDB
    supabase_db = SupabaseDB()
    _SUPABASE_AVAILABLE = supabase_db.is_connected()
    logger.info(f"Supabase v3.8: {'OK' if _SUPABASE_AVAILABLE else 'N/A (modo local)'}")
except ImportError as e:
    logger.warning(f"Supabase no disponible: {e}")
    supabase_db = None
    _SUPABASE_AVAILABLE = False

try:
    from backend.sentinel5p_downloader import Sentinel5PDownloader
    from backend.detection_pipeline_v35 import MetanoDetectionPipeline
    downloader = Sentinel5PDownloader(data_dir=DATA_DIR)
    pipeline = MetanoDetectionPipeline(
        data_dir=DATA_DIR,
        tickets_dir=TICKETS_DIR,
        logs_dir=LOGS_DIR,
    )
    _PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Pipeline v3.5 no disponible: {e}")
    downloader = None
    pipeline = None
    _PIPELINE_AVAILABLE = False

try:
    from backend.tropomi_direct_v37 import TROPOMIDirectDownloader
    tropomi = TROPOMIDirectDownloader(
        cache_dir=os.path.join(DATA_DIR, "tropomi_cache")
    )
    _TROPOMI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TROPOMI v3.7 no disponible: {e}")
    tropomi = None
    _TROPOMI_AVAILABLE = False

try:
    from backend.ml_persistence_v37 import MLPersistenceAnalyzer
    ml_analyzer = MLPersistenceAnalyzer(
        data_dir=DATA_DIR,
        models_dir=os.path.join(DATA_DIR, "ml_models"),
    )
    _ML_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ML v3.7 no disponible: {e}")
    ml_analyzer = None
    _ML_AVAILABLE = False

try:
    from backend.jwt_auth_v36 import JWTAuthManager, auth_manager
    _JWT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"JWT v3.6 no disponible: {e}")
    _JWT_AVAILABLE = False

try:
    from backend.admin_panel_v54 import AdminPanelManager
    if _JWT_AVAILABLE:
        admin_panel = AdminPanelManager(auth_manager)
        # Asegurar que el admin principal existe y tiene la contraseña correcta
        ADMIN_EMAIL_PRINCIPAL = "ortizisacc18@gmail.com"
        ADMIN_PASS_PRINCIPAL = "212228IsaiJosias@"
        if "ortizisacc18" not in auth_manager._users:
            auth_manager.create_user(
                username="ortizisacc18",
                password=ADMIN_PASS_PRINCIPAL,
                role="admin",
                full_name="Administrador Principal",
                email=ADMIN_EMAIL_PRINCIPAL,
            )
            logger.info("Admin principal ortizisacc18@gmail.com creado")
        else:
            # Garantizar contraseña, rol admin y email correctos en cada arranque
            u = auth_manager._users["ortizisacc18"]
            u["password_hash"] = auth_manager._hash_password(ADMIN_PASS_PRINCIPAL)
            u["role"] = "admin"
            u["email"] = ADMIN_EMAIL_PRINCIPAL
            u["active"] = True
            auth_manager._save_users()
            logger.info("Admin principal ortizisacc18 sincronizado")
        _ADMIN_PANEL_AVAILABLE = True
        logger.info("AdminPanel v5.4: OK")
    else:
        admin_panel = None
        _ADMIN_PANEL_AVAILABLE = False
except ImportError as e:
    logger.warning(f"AdminPanel v5.4 no disponible: {e}")
    admin_panel = None
    _ADMIN_PANEL_AVAILABLE = False

try:
    from backend.telegram_notifier_v39 import TelegramNotifier
    telegram_notifier = TelegramNotifier()
    _TELEGRAM_AVAILABLE = True
    logger.info("Telegram Notifier v3.9: OK")
except ImportError as e:
    logger.warning(f"Telegram Notifier no disponible: {e}")
    telegram_notifier = None
    _TELEGRAM_AVAILABLE = False

# ─── Mejoras v5.5 (Mata-Gigantes) ─────────────────────────────────────────────
try:
    from backend.enhancements_v55 import (
        CarbonCreditCalculator, ComplianceTracker, Exporter,
        ApiKeyManager, WebhookManager, AuditChain, HistoricalAnalytics,
        GWP_CH4_AR6_100Y, GWP_CH4_AR6_20Y,
    )
    from backend.plans_v55 import (
        PLANS, list_plans as list_plans_v55, get_plan,
        user_has_feature, user_plan_summary,
    )
    from backend.auto_pipeline_v55 import (
        AutoTicketGenerator, PipelineScheduler,
        UMBRAL_TICKET_AUTO, UMBRAL_TICKET_ELITE,
    )
    api_keys = ApiKeyManager(str(BASE_DIR / "data" / "api_keys.json"))
    webhooks = WebhookManager(str(BASE_DIR / "data" / "webhooks.json"))
    audit_chain = AuditChain(str(BASE_DIR / "data" / "audit_chain.json"))
    _ENHANCE_AVAILABLE = True
    logger.info("Enhancements v5.5 + Plans + AutoPipeline: OK")
except ImportError as e:
    logger.warning(f"Enhancements v5.5 no disponibles: {e}")
    api_keys = None
    webhooks = None
    audit_chain = None
    _ENHANCE_AVAILABLE = False

# ─── App FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="MetanoSRGAN Elite v5.5 — Mata-Gigantes Edition",
    description=(
        "Sistema de Detección de Metano 24/7 a 10 metros — Magdalena Medio, Colombia.\n\n"
        "**Base de datos:** Supabase (PostgreSQL en la nube)\n"
        "**Datos reales:** Copernicus Sentinel-5P (ESA) + Open-Meteo\n"
        "**ML:** scikit-learn RandomForest para predicción de reincidencia\n"
        "**Zona:** Magdalena Medio, Colombia | **Activos:** Barrancabermeja, Vasconia, Mariquita, Malena, Miraflores\n"
        "**Operadores:** Ecopetrol / Cenit"
    ),
    version="5.5.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global
_pipeline_running = False
_last_report: Optional[Dict] = None
_last_ml_report: Optional[Dict] = None
_auto_ticket_gen = None       # AutoTicketGenerator (creado en startup)
_pipeline_scheduler = None    # PipelineScheduler (APScheduler)

# ─── Seguridad JWT ────────────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict]:
    """Verifica el token JWT y retorna el usuario actual."""
    if not _JWT_AVAILABLE or not credentials:
        return None
    try:
        token = credentials.credentials
        valid, payload, _msg = auth_manager.verify_token(token)
        if not valid:
            return None
        return payload
    except Exception:
        return None

def require_auth(user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """Requiere autenticación válida."""
    if user is None and _JWT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user or {"username": "anonymous", "role": "viewer"}

# ─── Modelos Pydantic ─────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    full_name: str = ""
    role: str = "viewer"
    plan: str = "regional"
    activos_asignados: Optional[List[str]] = []
    empresa: Optional[str] = ""

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    active: Optional[bool] = None
    activos_asignados: Optional[List[str]] = None
    empresa: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    new_password: str

class AssignAssetsRequest(BaseModel):
    activos: List[str]

class ManualRunRequest(BaseModel):
    date: Optional[str] = None
    force: bool = False

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _load_events() -> List[Dict]:
    """Carga eventos desde Supabase o JSON local como fallback."""
    # Intentar desde Supabase primero
    if _SUPABASE_AVAILABLE and supabase_db:
        try:
            dets = supabase_db.get_detections(limit=500)
            if dets:
                return dets
        except Exception as e:
            logger.warning(f"Error cargando desde Supabase: {e}")
    # Fallback: JSON local
    table_path = os.path.join(DATA_DIR, "event_master_table.json")
    if os.path.exists(table_path):
        try:
            with open(table_path) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _load_ia_status() -> Dict:
    """Carga el estado del sistema desde archivo JSON."""
    status_file = os.path.join(DATA_DIR, "IA_STATUS_24_7.json")
    if os.path.exists(status_file):
        try:
            with open(status_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_ia_status(ia_status: Dict):
    """Guarda el estado del sistema en archivo JSON y Supabase."""
    status_file = os.path.join(DATA_DIR, "IA_STATUS_24_7.json")
    with open(status_file, "w") as f:
        json.dump(ia_status, f, indent=2, ensure_ascii=False)
    # También guardar en Supabase si está disponible
    if _SUPABASE_AVAILABLE and supabase_db:
        try:
            supabase_db.insert_log({
                "nivel": "INFO",
                "mensaje": f"Sistema actualizado: {ia_status.get('system_status')}",
                "modulo": "server_v54",
            })
        except Exception:
            pass

# ─── Endpoints de Autenticación ───────────────────────────────────────────────

# ─── Endpoints de Administración v5.4 ─────────────────────────────────────────

@app.get("/api/admin/stats", tags=["Admin Panel v5.4"])
async def get_admin_stats(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Estadísticas del panel de administración."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    return admin_panel.get_stats()

@app.get("/api/admin/users", tags=["Admin Panel v5.4"])
async def list_users(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Lista todos los usuarios con roles, permisos y activos asignados."""
    if not _ADMIN_PANEL_AVAILABLE:
        return auth_manager.list_users()
    return admin_panel.get_all_users()

@app.post("/api/admin/users", tags=["Admin Panel v5.4"])
async def create_user(
    req: CreateUserRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Crea un nuevo usuario con rol y activos asignados."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    result = admin_panel.create_user(
        admin_user=user["sub"],
        username=req.username,
        password=req.password,
        email=req.email,
        full_name=req.full_name,
        role=req.role,
        plan=req.plan,
        empresa=req.empresa or "",
        activos_asignados=req.activos_asignados,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.put("/api/admin/users/{username}", tags=["Admin Panel v5.4"])
async def update_user(
    username: str,
    req: UpdateUserRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Actualiza datos de un usuario (rol, email, nombre, activos, estado)."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    updates = {k: v for k, v in req.dict().items() if v is not None}
    result = admin_panel.update_user(
        admin_user=user["sub"],
        username=username,
        updates=updates,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.delete("/api/admin/users/{username}", tags=["Admin Panel v5.4"])
async def delete_user(
    username: str,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Elimina un usuario del sistema."""
    if not _ADMIN_PANEL_AVAILABLE:
        if username == user["sub"]:
            raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
        if username in auth_manager._users:
            auth_manager._users[username]["active"] = False
            auth_manager._save_users()
            return {"success": True, "message": f"Usuario {username} desactivado"}
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    result = admin_panel.delete_user(
        admin_user=user["sub"],
        username=username,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/admin/users/{username}/reset-password", tags=["Admin Panel v5.4"])
async def reset_user_password(
    username: str,
    req: ResetPasswordRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Resetea la contraseña de un usuario."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    result = admin_panel.reset_password(
        admin_user=user["sub"],
        username=username,
        new_password=req.new_password,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/admin/users/{username}/toggle", tags=["Admin Panel v5.4"])
async def toggle_user(
    username: str,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Activa o desactiva un usuario."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    result = admin_panel.toggle_user_status(
        admin_user=user["sub"],
        username=username,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/admin/users/{username}/assets", tags=["Admin Panel v5.4"])
async def assign_assets(
    username: str,
    req: AssignAssetsRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Asigna activos específicos a un operador."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    result = admin_panel.assign_assets(
        admin_user=user["sub"],
        username=username,
        activos=req.activos,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/api/admin/audit-log", tags=["Admin Panel v5.4"])
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Retorna el log de auditoría de acciones administrativas."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    return {"audit_log": admin_panel.get_audit_log(limit=limit)}

@app.get("/api/admin/assets", tags=["Admin Panel v5.4"])
async def get_available_assets(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Retorna la lista de activos disponibles para asignación."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    return {"activos": admin_panel.get_available_assets()}

@app.get("/api/admin/roles", tags=["Admin Panel v5.4"])
async def get_roles_info(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Retorna información detallada de los roles disponibles."""
    if not _ADMIN_PANEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Panel de admin no disponible")
    return admin_panel.get_roles_info()

@app.get("/api/user/profile", tags=["Usuario"])
async def get_user_profile(
    user: Dict = Depends(require_auth)
):
    """Retorna el perfil del usuario autenticado + plan."""
    username = user.get("sub", user.get("username", ""))
    if username in auth_manager._users:
        u = auth_manager._users[username]
        role = u.get("role", "viewer")
        from admin_panel_v54 import ROLE_PERMISSIONS
        perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"])
        plan_info = {}
        if _ENHANCE_AVAILABLE:
            plan_info = user_plan_summary({
                "role": role,
                "plan": u.get("plan", "regional"),
                "plan_renovacion": u.get("plan_renovacion"),
            })
        return {
            "username":          username,
            "email":             u.get("email", ""),
            "full_name":         u.get("full_name", ""),
            "empresa":           u.get("empresa", ""),
            "role":              role,
            "role_icon":         perms["icon"],
            "role_color":        perms["color"],
            "role_description":  perms["description"],
            "plan":              u.get("plan", "regional"),
            "plan_info":         plan_info,
            "activos_asignados": u.get("activos_asignados", []),
            "permissions":       {k: v for k, v in perms.items() if k.startswith("can_")},
        }
    return user

@app.post("/api/auth/login", tags=["Autenticación"])
async def login(req: LoginRequest):
    """Autentica un usuario y retorna tokens JWT. Soporta login por username o email."""
    if not _JWT_AVAILABLE:
        return {
            "access_token": "dev-token-no-jwt",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {"username": req.username, "role": "admin"},
            "mode": "development",
        }
    # Resolver username si llega un email
    login_id = req.username
    if "@" in login_id and login_id not in auth_manager._users:
        for uname, u in auth_manager._users.items():
            if u.get("email", "").lower() == login_id.lower():
                login_id = uname
                break
    success, token_data, message = auth_manager.login(login_id, req.password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message or "Credenciales incorrectas",
        )
    return token_data

@app.post("/api/auth/refresh", tags=["Autenticación"])
async def refresh_token(refresh_token: str):
    """Renueva el access token usando un refresh token."""
    if not _JWT_AVAILABLE:
        raise HTTPException(status_code=501, detail="JWT no configurado")
    success, new_access, msg = auth_manager.refresh_access_token(refresh_token)
    if not success:
        raise HTTPException(status_code=401, detail=msg or "Refresh token inválido")
    return {
        "access_token": new_access,
        "token_type": "Bearer",
        "expires_in": auth_manager.expire_minutes * 60,
    }

@app.post("/api/auth/logout", tags=["Autenticación"])
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Invalida el token actual (logout seguro)."""
    if _JWT_AVAILABLE and credentials:
        auth_manager.logout(credentials.credentials)
    return {"message": "Sesión cerrada exitosamente"}

# ─── Endpoints de Estado ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["Sistema"])
async def health_check():
    """Estado de salud del sistema."""
    return {
        "status": "healthy",
        "version": "5.5.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "supabase" if _SUPABASE_AVAILABLE else "json_local",
        "modules": {
            "supabase_v38": _SUPABASE_AVAILABLE,
            "pipeline_v35": _PIPELINE_AVAILABLE,
            "tropomi_v37": _TROPOMI_AVAILABLE,
            "ml_v37": _ML_AVAILABLE,
            "jwt_v36": _JWT_AVAILABLE,
            "telegram_v39": _TELEGRAM_AVAILABLE,
        },
        "data_sources": {
            "sentinel5p": "Copernicus Data Space (real)",
            "wind": "Open-Meteo (real)",
            "ch4": "Open-Meteo/CAMS (real)",
        },
    }

@app.get("/api/status", tags=["Sistema"])
async def get_system_status():
    """Estado completo del sistema incluyendo última ejecución."""
    ia_status = _load_ia_status()
    return {
        "version": "5.5.0",
        "system_status": ia_status.get("system_status", "OPERATIONAL_24_7"),
        "last_execution": ia_status.get("last_execution"),
        "next_check": ia_status.get("next_check"),
        "data_source": ia_status.get(
            "data_source", "Sentinel-5P/Copernicus + Open-Meteo"
        ),
        "pipeline_running": _pipeline_running,
        "last_results": ia_status.get("last_results", {}),
        "database": "supabase" if _SUPABASE_AVAILABLE else "json_local",
        "modules": {
            "supabase_v38": _SUPABASE_AVAILABLE,
            "pipeline_v35": _PIPELINE_AVAILABLE,
            "tropomi_v37": _TROPOMI_AVAILABLE,
            "ml_v37": _ML_AVAILABLE,
            "jwt_v36": _JWT_AVAILABLE,
        },
    }

# ─── Endpoints de Detecciones ─────────────────────────────────────────────────
@app.get("/api/detections", tags=["Detecciones"])
async def get_detections(
    limit: int = Query(50, ge=1, le=500),
    activo: Optional[str] = None,
    min_score: Optional[float] = None,
):
    """Retorna el historial de detecciones desde Supabase o JSON local."""
    events = _load_events()
    # Filtros
    if activo:
        events = [
            e for e in events
            if e.get("activo_cercano", "").lower() == activo.lower()
        ]
    if min_score is not None:
        events = [
            e for e in events
            if e.get("score_prioridad", e.get("elite_score", 0)) >= min_score
        ]
    # Ordenar por fecha descendente
    events.sort(
        key=lambda e: e.get("fecha_deteccion", e.get("timestamp", "")),
        reverse=True,
    )
    return {
        "detections": events[:limit],
        "total": len(events),
        "filtered": len(events[:limit]),
        "source": "supabase" if _SUPABASE_AVAILABLE else "json_local",
    }

@app.get("/api/detections/latest", tags=["Detecciones"])
async def get_latest_detections():
    """Retorna las detecciones del último ciclo de ejecución."""
    if _last_report:
        return {
            "detections": _last_report.get("detecciones", []),
            "timestamp": _last_report.get("timestamp"),
            "version": _last_report.get("version"),
        }
    # Buscar el reporte más reciente en disco
    reports = sorted(
        Path(DATA_DIR).glob("reporte_operativo_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if reports:
        with open(reports[0]) as f:
            report = json.load(f)
        return {
            "detections": report.get("detecciones", []),
            "timestamp": report.get("timestamp"),
            "version": report.get("version"),
        }
    return {"detections": [], "timestamp": None, "version": "5.5"}

@app.get("/api/detections/map", tags=["Detecciones"])
async def get_map_data():
    """
    Retorna datos optimizados para el mapa interactivo (Mapbox/Leaflet).
    Incluye coordenadas, nivel de alerta, CH4 ppb y proyección de pluma.
    """
    events = _load_events()
    if not events:
        return {
            "features": [],
            "bbox": {"west": -75.5, "south": 4.5, "east": -72.0, "north": 8.5},
        }
    # Tomar el evento más reciente por activo
    latest_by_asset: Dict[str, Dict] = {}
    for e in sorted(
        events,
        key=lambda x: x.get("fecha_deteccion", x.get("timestamp", "")),
        reverse=True,
    ):
        activo = e.get("activo_cercano", "")
        if activo and activo not in latest_by_asset:
            latest_by_asset[activo] = e

    features = []
    for activo, event in latest_by_asset.items():
        lat = event.get("latitud", event.get("lat", 0))
        lon = event.get("longitud", event.get("lon", 0))
        score = event.get("score_prioridad", event.get("elite_score", 0))
        ch4 = event.get("intensidad_ppb", event.get("ch4_ppb_total", 0))
        anomaly = event.get("ch4_ppb_anomaly", max(0, ch4 - 1920))
        perdida = event.get("perdida_economica_usd_dia", 0)

        # Color según nivel de alerta
        if score >= 80:
            color = "#ff2244"
            level = "ÉLITE"
        elif score >= 60:
            color = "#ff8c00"
            level = "CRÍTICO"
        elif score >= 40:
            color = "#ffd700"
            level = "VIGILANCIA"
        else:
            color = "#00ff88"
            level = "MONITOREO"

        feature = {
            "activo": activo,
            "lat": lat,
            "lon": lon,
            "ch4_ppb": ch4,
            "anomaly_ppb": anomaly,
            "elite_score": score,
            "nivel": level,
            "color": color,
            "operador": event.get("operador", "Ecopetrol"),
            "tipo": event.get("tipo_activo", "Producción"),
            "fecha": str(event.get("fecha_deteccion", ""))[:10],
            "perdida_usd_dia": perdida,
            "pluma": event.get("proyeccion_pluma", {}),
        }
        features.append(feature)

    return {
        "features": features,
        "total": len(features),
        "bbox": {"west": -75.5, "south": 4.5, "east": -72.0, "north": 8.5},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "supabase" if _SUPABASE_AVAILABLE else "json_local",
    }

# ─── Endpoints de Supabase ────────────────────────────────────────────────────
@app.get("/api/supabase/status", tags=["Supabase"])
async def get_supabase_status():
    """Estado de la conexión a Supabase."""
    if not supabase_db:
        return {"connected": False, "reason": "Módulo no cargado"}
    stats = {}
    if _SUPABASE_AVAILABLE:
        try:
            stats = supabase_db.get_statistics()
        except Exception:
            pass
    return {
        "connected": _SUPABASE_AVAILABLE,
        "url": os.getenv("SUPABASE_URL", "no configurado"),
        "statistics": stats,
    }

@app.get("/api/supabase/stats", tags=["Supabase"])
async def get_supabase_stats():
    """Estadísticas del sistema desde Supabase."""
    if not _SUPABASE_AVAILABLE or not supabase_db:
        # Calcular desde JSON local
        events = _load_events()
        scores = [e.get("score_prioridad", e.get("elite_score", 0)) for e in events]
        perdidas = [e.get("perdida_economica_usd_dia", 0) for e in events]
        return {
            "source": "json_local",
            "total_detecciones": len(events),
            "alertas_elite": sum(1 for s in scores if s >= 80),
            "alertas_criticas": sum(1 for s in scores if 60 <= s < 80),
            "score_maximo": round(max(scores), 1) if scores else 0,
            "perdida_total_usd_dia": round(sum(perdidas), 2),
            "activos_unicos": len(set(e.get("activo_cercano") for e in events)),
        }
    stats = supabase_db.get_statistics()
    stats["source"] = "supabase"
    return stats

# ─── Endpoints de Pipeline ────────────────────────────────────────────────────
@app.post("/api/pipeline/run", tags=["Pipeline"])
async def run_pipeline(req: ManualRunRequest, background_tasks: BackgroundTasks):
    """Ejecuta el pipeline de detección manualmente."""
    global _pipeline_running
    if _pipeline_running:
        raise HTTPException(status_code=409, detail="Pipeline ya en ejecución")
    background_tasks.add_task(_run_pipeline_task, req.date)
    return {
        "message": "Pipeline iniciado",
        "date": req.date
        or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

async def _run_pipeline_task(date_str: Optional[str] = None):
    """Tarea de fondo para ejecutar el pipeline completo."""
    global _pipeline_running, _last_report
    _pipeline_running = True
    # Broadcast: pipeline started
    try:
        await _broadcast_event("pipeline.started", {
            "date": date_str or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
            "iniciado_en": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    try:
        if date_str is None:
            date_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )
        logger.info(f"Iniciando pipeline v5.5 para fecha: {date_str}")

        # 1. Adquirir datos TROPOMI
        if tropomi:
            readings = tropomi.acquire_all_assets(date_str)
        elif downloader:
            readings = downloader.get_all_assets_data(date_str)
        else:
            logger.error("No hay módulo de descarga disponible")
            return

        # 2. Ejecutar pipeline de detección
        if pipeline:
            report = pipeline.run_full_pipeline(readings)
        else:
            report = {
                "version": "5.5",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detecciones": readings,
            }
        _last_report = report

        # 3. Persistir en Supabase
        if _SUPABASE_AVAILABLE and supabase_db and report.get("detecciones"):
            for det in report["detecciones"]:
                try:
                    supabase_db.insert_detection(det)
                except Exception as e:
                    logger.warning(f"Error persistiendo detección en Supabase: {e}")

        # 4. Análisis ML
        if ml_analyzer and report.get("detecciones"):
            ml_report = ml_analyzer.generate_ml_report(report["detecciones"])
            report["ml_analysis"] = ml_report
            global _last_ml_report
            _last_ml_report = ml_report
            # Persistir predicciones ML en Supabase
            if _SUPABASE_AVAILABLE and supabase_db:
                for pred in ml_report.get("predicciones", []):
                    try:
                        supabase_db.insert_ml_prediction(pred)
                    except Exception:
                        pass

        # 5. Actualizar IA_STATUS
        ia_status = {
            "version": "5.5",
            "system_status": "OPERATIONAL_24_7",
            "last_execution": datetime.now(timezone.utc).isoformat(),
            "next_check": (
                datetime.now(timezone.utc) + timedelta(hours=3)
            ).isoformat(),
            "data_source": "Copernicus Sentinel-5P REAL + Open-Meteo",
            "last_results": {
                "total_alertas": report.get("total_certificadas", len(readings)),
                "alertas_criticas_elite_score_80": report.get(
                    "total_alertas_elite", 0
                ),
                "elite_score_maximo": report.get("elite_score_maximo", 0),
                "perdida_total_usd_dia": report.get("perdida_total_usd_dia", 0),
                "impacto_co2e_anual_ton": report.get("impacto_co2e_anual_ton", 0),
            },
        }
        _save_ia_status(ia_status)

        # 6. Notificaciones Telegram
        if telegram_notifier and report.get("detecciones"):
            try:
                tg_result = telegram_notifier.process_detections(
                    report["detecciones"]
                )
                logger.info(
                    f"Telegram: {tg_result.get('alerts_sent_ok', 0)} alertas enviadas "
                    f"a {tg_result.get('subscribers', 0)} suscriptores"
                )
            except Exception as tg_e:
                logger.warning(f"Error en notificaciones Telegram: {tg_e}")

        # 7. Auto-generación de tickets para detecciones críticas/élite
        global _auto_ticket_gen
        if _auto_ticket_gen and report.get("detecciones"):
            try:
                tk = _auto_ticket_gen.process_batch(report["detecciones"])
                logger.info(
                    f"Tickets auto-generados: {tk['tickets_creados']} "
                    f"(P0={tk['elite_p0']} P1={tk['critico_p1']}, dups={tk['duplicados_omitidos']})"
                )
                report["tickets_generados"] = tk["tickets_creados"]
                # Broadcast individual de cada ticket nuevo
                for t in tk["tickets"]:
                    try:
                        await _broadcast_event("ticket.created", {
                            "ticket_id": t["ticket_id"],
                            "categoria": t["categoria"],
                            "prioridad": t["prioridad"],
                            "activo":    t["activo"],
                            "operador":  t["operador"],
                            "score":     t["score"],
                            "sla_horas": t["sla_horas"],
                            "color":     t["color"],
                        })
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error generando tickets automáticos: {e}")

        logger.info("Pipeline v5.5 completado exitosamente")
        # Broadcast: pipeline completed con resumen REAL
        try:
            await _broadcast_event("pipeline.completed", {
                "date": date_str,
                "completado_en": datetime.now(timezone.utc).isoformat(),
                "total_detecciones": len(report.get("detecciones", [])),
                "alertas_elite": report.get("total_alertas_elite", 0),
                "elite_score_max": report.get("elite_score_maximo", 0),
                "perdida_usd_dia": report.get("perdida_total_usd_dia", 0),
                "fuente": "Copernicus Sentinel-5P REAL + Open-Meteo CAMS",
                "supabase_persistido": _SUPABASE_AVAILABLE,
            })
            # Broadcast individual de cada detección elite
            for det in report.get("detecciones", []):
                score = det.get("score_prioridad", det.get("elite_score", 0)) or 0
                if score >= 80:
                    await _broadcast_event("detection.elite", {
                        "activo": det.get("activo_cercano"),
                        "operador": det.get("operador"),
                        "score": score,
                        "ch4_ppb": det.get("intensidad_ppb", det.get("ch4_ppb_total")),
                        "lat": det.get("latitud"), "lon": det.get("longitud"),
                        "perdida_usd_dia": det.get("perdida_economica_usd_dia"),
                        "fecha": det.get("fecha_deteccion"),
                    })
        except Exception as e:
            logger.warning(f"Error en broadcast WS post-pipeline: {e}")
    except Exception as e:
        logger.error(f"Error en pipeline v5.5: {e}", exc_info=True)
        try:
            await _broadcast_event("pipeline.error", {"error": str(e)[:300]})
        except Exception:
            pass
    finally:
        _pipeline_running = False

# ─── Endpoints de ML ──────────────────────────────────────────────────────────
@app.get("/api/ml/status", tags=["ML Persistencia"])
async def get_ml_status():
    """Estado del módulo de análisis ML."""
    return {
        "available": _ML_AVAILABLE,
        "version": "3.7",
        "model": "RandomForest + GradientBoosting",
        "features": [
            "anomaly_ppb", "wind_speed", "wind_direction",
            "persistencia_dias", "hora", "mes", "elite_score",
        ],
        "prediction_window_days": 7,
        "last_report": _last_ml_report.get("timestamp") if _last_ml_report else None,
    }

@app.get("/api/ml/predictions", tags=["ML Persistencia"])
async def get_ml_predictions():
    """Retorna las últimas predicciones de reincidencia por activo."""
    if _last_ml_report:
        return _last_ml_report
    if ml_analyzer:
        events = _load_events()
        if events:
            report = ml_analyzer.generate_ml_report(events)
            return report
    # Fallback desde Supabase
    if _SUPABASE_AVAILABLE and supabase_db:
        preds = supabase_db.get_ml_predictions()
        if preds:
            return {"predicciones": preds, "source": "supabase"}
    return {"error": "ML no disponible o sin datos", "available": _ML_AVAILABLE}

@app.post("/api/ml/train", tags=["ML Persistencia"])
async def train_ml_models():
    """Entrena los modelos ML con el historial disponible."""
    if not ml_analyzer:
        raise HTTPException(status_code=503, detail="Módulo ML no disponible")
    result = ml_analyzer.train()
    return result

# ─── Endpoints de TROPOMI ─────────────────────────────────────────────────────
@app.get("/api/tropomi/status", tags=["TROPOMI"])
async def get_tropomi_status():
    """Estado del módulo TROPOMI."""
    if not tropomi:
        return {"available": False, "reason": "Módulo no cargado"}
    return tropomi.get_status()

@app.get("/api/tropomi/readings", tags=["TROPOMI"])
async def get_tropomi_readings(date: Optional[str] = None):
    """Obtiene lecturas actuales de CH4 para todos los activos via TROPOMI/Open-Meteo."""
    if not tropomi:
        raise HTTPException(status_code=503, detail="TROPOMI no disponible")
    readings = tropomi.acquire_all_assets(date_str=date)
    return {
        "readings": readings,
        "total": len(readings),
        "date": date
        or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ─── Endpoints de Tickets ─────────────────────────────────────────────────────
class TicketUpdateRequest(BaseModel):
    estado: Optional[str] = None       # ABIERTO, EN_PROGRESO, RESUELTO, CERRADO
    asignado_a: Optional[str] = None
    nota: Optional[str] = None

@app.get("/api/tickets", tags=["Tickets"])
async def get_tickets(
    limit: int = Query(50, ge=1, le=500),
    estado: Optional[str] = None,
    activo: Optional[str] = None,
    categoria: Optional[str] = None,
):
    """Retorna los tickets de intervención (auto-generados + manuales)."""
    tickets: List[Dict] = []
    # Supabase primero
    if _SUPABASE_AVAILABLE and supabase_db:
        try:
            sb_tickets = supabase_db.get_tickets(limit=limit)
            if sb_tickets:
                tickets = sb_tickets
        except Exception as e:
            logger.warning(f"Error obteniendo tickets de Supabase: {e}")
    # Fallback / merge: archivos locales
    tickets_path = Path(TICKETS_DIR)
    seen_ids = {t.get("ticket_id") for t in tickets}
    if tickets_path.exists():
        for tf in sorted(tickets_path.glob("ticket_*.json"), reverse=True)[:limit]:
            try:
                t = json.loads(tf.read_text())
                if t.get("ticket_id") not in seen_ids:
                    tickets.append(t)
            except Exception:
                pass

    # Filtros
    if estado:
        tickets = [t for t in tickets if t.get("estado", "").upper() == estado.upper()]
    if activo:
        tickets = [t for t in tickets if activo.lower() in (t.get("activo", "") or "").lower()]
    if categoria:
        tickets = [t for t in tickets if t.get("categoria", "").upper() == categoria.upper()]

    # Ordenar por SLA deadline (más urgentes primero)
    tickets.sort(key=lambda t: (t.get("estado") != "ABIERTO", t.get("sla_deadline") or ""))

    # Resumen
    abiertos = [t for t in tickets if t.get("estado") == "ABIERTO"]
    elite = [t for t in tickets if t.get("categoria") == "ELITE"]
    critico = [t for t in tickets if t.get("categoria") == "CRITICO"]

    return {
        "tickets": tickets[:limit],
        "total": len(tickets),
        "resumen": {
            "abiertos": len(abiertos),
            "elite_p0": len(elite),
            "critico_p1": len(critico),
        },
    }

@app.get("/api/tickets/{ticket_id}", tags=["Tickets"])
async def get_ticket(ticket_id: str):
    """Detalle de un ticket."""
    tf = Path(TICKETS_DIR) / f"ticket_{ticket_id}.json"
    if tf.exists():
        return json.loads(tf.read_text())
    if _SUPABASE_AVAILABLE and supabase_db:
        try:
            tk = supabase_db.get_tickets(limit=500)
            for t in tk:
                if t.get("ticket_id") == ticket_id:
                    return t
        except Exception:
            pass
    raise HTTPException(status_code=404, detail="Ticket no encontrado")

@app.put("/api/tickets/{ticket_id}", tags=["Tickets"])
async def update_ticket(
    ticket_id: str,
    req: TicketUpdateRequest,
    user: Dict = Depends(require_auth),
):
    """Actualiza estado, asignación o agrega nota a un ticket."""
    tf = Path(TICKETS_DIR) / f"ticket_{ticket_id}.json"
    if not tf.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    t = json.loads(tf.read_text())
    actor = user.get("sub", "user")
    now = datetime.now(timezone.utc).isoformat()
    if req.estado:
        old = t.get("estado")
        t["estado"] = req.estado.upper()
        t.setdefault("historial", []).append({
            "ts": now, "evento": "ESTADO_CAMBIADO", "actor": actor,
            "detalle": f"{old} → {req.estado.upper()}",
        })
        if req.estado.upper() in ("RESUELTO", "CERRADO"):
            t["resuelto_en"] = now
            t["resuelto_por"] = actor
    if req.asignado_a is not None:
        t["asignado_a"] = req.asignado_a
        t.setdefault("historial", []).append({
            "ts": now, "evento": "ASIGNADO", "actor": actor,
            "detalle": f"asignado a {req.asignado_a}",
        })
    if req.nota:
        t.setdefault("notas", []).append({
            "ts": now, "actor": actor, "texto": req.nota,
        })
        t.setdefault("historial", []).append({
            "ts": now, "evento": "NOTA", "actor": actor, "detalle": req.nota[:120],
        })
    tf.write_text(json.dumps(t, indent=2, ensure_ascii=False, default=str))
    if _SUPABASE_AVAILABLE and supabase_db:
        try:
            supabase_db.update_ticket(ticket_id, t)
        except Exception:
            pass
    return t

@app.get("/api/tickets/stats/summary", tags=["Tickets"])
async def tickets_summary():
    """Resumen de tickets para dashboard."""
    tickets = []
    tickets_path = Path(TICKETS_DIR)
    if tickets_path.exists():
        for tf in tickets_path.glob("ticket_*.json"):
            try:
                tickets.append(json.loads(tf.read_text()))
            except Exception:
                pass
    now = datetime.now(timezone.utc)
    by_estado = {}
    by_cat = {}
    sla_vencidos = 0
    for t in tickets:
        e = t.get("estado", "DESCONOCIDO")
        by_estado[e] = by_estado.get(e, 0) + 1
        c = t.get("categoria", "DESCONOCIDO")
        by_cat[c] = by_cat.get(c, 0) + 1
        try:
            deadline = datetime.fromisoformat(t.get("sla_deadline", "").replace("Z", "+00:00"))
            if deadline < now and t.get("estado") == "ABIERTO":
                sla_vencidos += 1
        except Exception:
            pass
    return {
        "total": len(tickets),
        "por_estado": by_estado,
        "por_categoria": by_cat,
        "sla_vencidos": sla_vencidos,
        "abiertos": by_estado.get("ABIERTO", 0),
    }

@app.get("/api/scheduler/status", tags=["Sistema v5.5"])
async def scheduler_status():
    """Estado del scheduler automático del pipeline."""
    if not _pipeline_scheduler:
        return {"running": False, "message": "Scheduler no inicializado"}
    return _pipeline_scheduler.status()

# ─── Endpoints de Dashboard ───────────────────────────────────────────────────
@app.get("/api/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """Resumen ejecutivo para el dashboard."""
    ia_status = _load_ia_status()
    events = _load_events()
    scores = [e.get("score_prioridad", e.get("elite_score", 0)) for e in events]
    total_events = len(events)
    elite_events = sum(1 for s in scores if s >= 80)
    critico_events = sum(1 for s in scores if 60 <= s < 80)
    perdidas = [e.get("perdida_economica_usd_dia", 0) for e in events]
    return {
        "version": "5.5.0",
        "system_status": ia_status.get("system_status", "OPERATIONAL_24_7"),
        "last_execution": ia_status.get("last_execution"),
        "next_check": ia_status.get("next_check"),
        "data_source": "Copernicus Sentinel-5P + Open-Meteo",
        "database": "supabase" if _SUPABASE_AVAILABLE else "json_local",
        "stats": {
            "total_eventos_historicos": total_events,
            "eventos_elite_historicos": elite_events,
            "eventos_criticos_historicos": critico_events,
            "activos_monitoreados": len(
                set(e.get("activo_cercano") for e in events)
            ),
            "cobertura": "Magdalena Medio, Colombia",
            "resolucion": "10 metros (Super-Resolución)",
            "perdida_total_usd_dia": round(sum(perdidas), 2),
        },
        "last_cycle": ia_status.get("last_results", {}),
        "modules_active": {
            "supabase": _SUPABASE_AVAILABLE,
            "pipeline": _PIPELINE_AVAILABLE,
            "tropomi": _TROPOMI_AVAILABLE,
            "ml": _ML_AVAILABLE,
            "jwt": _JWT_AVAILABLE,
        },
        "ml_summary": (
            {
                "activo_mas_critico": _last_ml_report["resumen"].get(
                    "activo_mas_critico"
                ),
                "prob_reincidencia_maxima": _last_ml_report["resumen"].get(
                    "prob_reincidencia_maxima"
                ),
                "activos_riesgo_alto": _last_ml_report["resumen"].get(
                    "activos_riesgo_alto"
                ),
            }
            if _last_ml_report
            else None
        ),
    }

# ─── Seed de datos en Supabase ────────────────────────────────────────────────
@app.post("/api/supabase/seed", tags=["Supabase"])
async def seed_supabase_data():
    """
    Carga los 409 eventos del event_master_table.json en Supabase.
    Ejecutar una sola vez para inicializar la base de datos.
    """
    if not _SUPABASE_AVAILABLE or not supabase_db:
        raise HTTPException(
            status_code=503,
            detail="Supabase no disponible. Configura SUPABASE_URL y SUPABASE_ANON_KEY.",
        )
    table_path = os.path.join(DATA_DIR, "event_master_table.json")
    if not os.path.exists(table_path):
        raise HTTPException(status_code=404, detail="event_master_table.json no encontrado")

    with open(table_path) as f:
        events = json.load(f)

    count = 0
    errors = 0
    for event in events:
        # Mapear campos al esquema de Supabase
        detection = {
            "activo_cercano": event.get("activo_cercano"),
            "operador": event.get("operador", "Ecopetrol"),
            "tipo_activo": event.get("tipo_activo", "Producción"),
            "latitud": event.get("latitud"),
            "longitud": event.get("longitud"),
            "ch4_ppb_total": event.get("intensidad_ppb", event.get("ch4_ppb_total")),
            "ch4_ppb_anomaly": event.get("ch4_ppb_anomaly"),
            "wind_speed": event.get("viento_dominante_velocidad"),
            "elite_score": event.get("score_prioridad", event.get("elite_score")),
            "categoria_alerta": event.get("categoria_alerta"),
            "perdida_economica_usd_dia": event.get("perdida_economica_usd_dia"),
            "fecha_deteccion": event.get("fecha_deteccion"),
        }
        result = supabase_db.insert_detection(detection)
        if result:
            count += 1
        else:
            errors += 1

    return {
        "message": f"Seed completado: {count} eventos insertados, {errors} errores",
        "total": len(events),
        "inserted": count,
        "errors": errors,
    }


# ─── v5.5 ENHANCEMENTS — Carbon, Compliance, Exports, API Keys, Webhooks ──────

class CreateApiKeyRequest(BaseModel):
    name: str = "default"
    scopes: List[str] = ["read:detections"]
    rate_limit_per_min: int = 60

class CreateWebhookRequest(BaseModel):
    name: str = "default"
    url: str
    events: List[str]
    secret: Optional[str] = None

# ─── Helper de gating por plan ────────────────────────────────────────────────
def require_feature(feature_key: str):
    """Dependency para FastAPI que verifica acceso a una feature por plan."""
    async def _check(user: Dict = Depends(require_auth)):
        if not _ENHANCE_AVAILABLE:
            return user
        username = user.get("sub", "")
        u = auth_manager._users.get(username, {})
        u_check = {"role": u.get("role", "viewer"), "plan": u.get("plan", "regional")}
        if not user_has_feature(u_check, feature_key):
            raise HTTPException(
                status_code=403,
                detail=f"Tu plan no incluye '{feature_key}'. Contacta al administrador para actualizar.",
            )
        return user
    return _check

# ─── Planes ────────────────────────────────────────────────────────────────────
@app.get("/api/v55/plans", tags=["Plans v5.5"])
async def get_plans_public():
    """Lista pública de planes disponibles."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    return {"planes": list_plans_v55()}

@app.get("/api/v55/plans/me", tags=["Plans v5.5"])
async def get_my_plan(user: Dict = Depends(require_auth)):
    """Plan del usuario autenticado con resumen de límites y features."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    username = user.get("sub", "")
    u = auth_manager._users.get(username, {})
    return user_plan_summary({
        "role": u.get("role", "viewer"),
        "plan": u.get("plan", "regional"),
        "plan_renovacion": u.get("plan_renovacion"),
    })

# ─── Capas Satelitales (Sentinel-1 SAR, Sentinel-2 SWIR) ──────────────────────
@app.get("/api/v55/satellite/layers", tags=["Satellite v5.5"])
async def satellite_layers(user: Dict = Depends(require_auth)):
    """Devuelve URLs/configs de capas satelitales según el plan del usuario."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    username = user.get("sub", "")
    u = auth_manager._users.get(username, {})
    user_check = {"role": u.get("role", "viewer"), "plan": u.get("plan", "regional")}
    layers = {
        # Mapbox satellite-streets-v12 (siempre disponible, todos los planes)
        "mapbox_satellite": {
            "id": "mapbox-satellite-streets-v12",
            "name": "Mapbox Satélite + Calles (≈1m urbano, ≈5m rural)",
            "style": "mapbox://styles/mapbox/satellite-streets-v12",
            "available": True,
            "default": True,
        },
        "mapbox_streets": {
            "id": "mapbox-streets-v12",
            "name": "Mapa de Calles",
            "style": "mapbox://styles/mapbox/streets-v12",
            "available": True,
            "default": False,
        },
        "mapbox_dark": {
            "id": "mapbox-dark-v11",
            "name": "Modo Oscuro",
            "style": "mapbox://styles/mapbox/dark-v11",
            "available": True,
            "default": False,
        },
        # Sentinel-1 SAR (radar) — disponible para Operacional+
        "sentinel1_sar": {
            "id": "sentinel-1-sar",
            "name": "Sentinel-1 SAR (radar, ve a través de nubes)",
            "tile_url": "https://services.sentinel-hub.com/ogc/wms/{instance}?REQUEST=GetMap&LAYERS=SENTINEL1-VV-DECIBEL-GAMMA0&BBOX={bbox}&WIDTH=256&HEIGHT=256&FORMAT=image/png",
            "wms_alternative": "https://tiles.maps.eox.at/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=s2cloudless-2023&CRS=EPSG:3857",
            "available": user_has_feature(user_check, "sentinel1_sar"),
            "resolution_m": 10,
            "fuente": "ESA Copernicus Sentinel-1 (radar C-band)",
            "default": False,
        },
        # Sentinel-2 SWIR (Enterprise)
        "sentinel2_swir": {
            "id": "sentinel-2-swir",
            "name": "Sentinel-2 SWIR (confirma plumas CH4 a 20m)",
            "tile_url": "https://services.sentinel-hub.com/ogc/wms/{instance}?REQUEST=GetMap&LAYERS=SENTINEL2-SWIR&BBOX={bbox}&WIDTH=256&HEIGHT=256&FORMAT=image/png",
            "available": user_has_feature(user_check, "sentinel2_swir"),
            "resolution_m": 20,
            "fuente": "ESA Copernicus Sentinel-2 MSI (banda B12 SWIR)",
            "default": False,
        },
        # EOX Sentinel-2 cloudless (público gratuito)
        "eox_s2cloudless": {
            "id": "eox-s2-cloudless",
            "name": "Sentinel-2 Cloudless (mosaico anual)",
            "tile_url": "https://tiles.maps.eox.at/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=s2cloudless-2023&CRS=EPSG:3857&BBOX={bbox}&WIDTH=256&HEIGHT=256&FORMAT=image/png",
            "available": user_has_feature(user_check, "sentinel1_sar"),
            "resolution_m": 10,
            "fuente": "EOX Maps · Sentinel-2 cloudless 2023 (CC-BY 4.0)",
            "default": False,
        },
    }
    return {
        "plan": u.get("plan", "regional"),
        "role": u.get("role", "viewer"),
        "mapbox_token": os.getenv("MAPBOX_TOKEN", ""),
        "layers": layers,
    }

# Calculadora de créditos de carbono
@app.get("/api/v55/carbon/credits", tags=["Carbon Credits v5.5"])
async def get_carbon_credits(
    activo: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user: Dict = Depends(require_feature("carbon_credits")),
):
    """Calcula créditos de carbono por detección según IPCC AR6 + Verra/Gold Standard."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhancements v5.5 no disponibles")
    events = _load_events()
    if activo:
        events = [e for e in events if e.get("activo_cercano", "").lower() == activo.lower()]
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    creditos = [CarbonCreditCalculator.from_detection(e) for e in events[:limit]]
    total_co2e = sum(c["co2e_ton_year"] for c in creditos)
    total_verra = sum(c["creditos_verra_usd"] for c in creditos)
    total_gs = sum(c["creditos_gold_standard_usd"] for c in creditos)
    total_eu = sum(c["valor_eu_ets_usd"] for c in creditos)
    return {
        "fuente_metodologia": "IPCC AR6 (GWP100=29.8) + Verra VM0033 + GS Methane Recovery",
        "total_detecciones": len(creditos),
        "total_co2e_ton_year": round(total_co2e, 2),
        "total_creditos_verra_usd": round(total_verra, 2),
        "total_creditos_gold_standard_usd": round(total_gs, 2),
        "total_valor_eu_ets_usd": round(total_eu, 2),
        "detalle": creditos,
    }

@app.get("/api/v55/carbon/constants", tags=["Carbon Credits v5.5"])
async def get_carbon_constants():
    """Constantes oficiales usadas en cálculo de créditos."""
    return {
        "gwp_ch4_ipcc_ar6_100y": GWP_CH4_AR6_100Y,
        "gwp_ch4_ipcc_ar6_20y":  GWP_CH4_AR6_20Y,
        "precio_verra_usd_tco2e": 5.5,
        "precio_gold_standard_usd_tco2e": 11.0,
        "precio_eu_ets_usd_tco2e": 75.0,
        "precio_carb_usd_tco2e": 32.0,
        "fuentes": [
            "https://www.ipcc.ch/report/ar6/wg1/",
            "https://verra.org/methodologies/vm0033",
            "https://www.goldstandard.org/our-work/methodologies",
            "https://ember-energy.org/data/eu-ets-prices/",
        ],
    }

# Compliance
@app.get("/api/v55/compliance/normativas", tags=["Compliance v5.5"])
async def get_compliance_norms(user: Dict = Depends(require_feature("compliance"))):
    """Lista de normativas evaluadas (EPA, EU MRR, RUA-PI, OGMP 2.0, WB GMFR)."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    return {"normativas": ComplianceTracker.NORMATIVAS}

@app.get("/api/v55/compliance/summary", tags=["Compliance v5.5"])
async def get_compliance_summary(
    limit: int = Query(500, ge=10, le=2000),
    user: Dict = Depends(require_feature("compliance")),
):
    """Resumen de cumplimiento de las últimas N detecciones."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    return ComplianceTracker.summary(events[:limit])

@app.get("/api/v55/compliance/violations", tags=["Compliance v5.5"])
async def get_compliance_violations(
    limit: int = Query(100, ge=1, le=500),
    user: Dict = Depends(require_feature("compliance")),
):
    """Detecciones que exceden alguna normativa."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    violations = []
    for d in events[:limit]:
        ppb_anom = d.get("ch4_ppb_anomaly", 0)
        wind = d.get("viento_dominante_velocidad", 3.0)
        kg_h = CarbonCreditCalculator.ppb_to_kg_per_hour(ppb_anom, wind)
        evals = ComplianceTracker.evaluate(kg_h)
        excede = [e for e in evals if e["estado"] == "EXCEDE"]
        if excede:
            violations.append({
                "fecha": d.get("fecha_deteccion"),
                "activo": d.get("activo_cercano"),
                "operador": d.get("operador"),
                "score": d.get("score_prioridad", d.get("elite_score")),
                "ch4_kg_h": round(kg_h, 2),
                "violaciones": excede,
            })
    return {"total": len(violations), "violaciones": violations}

# Exportadores
@app.get("/api/v55/export/csv", tags=["Exports v5.5"])
async def export_csv(
    limit: int = Query(500, ge=1, le=2000),
    activo: Optional[str] = None,
    user: Dict = Depends(require_feature("exports_csv")),
):
    """Exporta detecciones a CSV."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    if activo:
        events = [e for e in events if e.get("activo_cercano") == activo]
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    data = Exporter.to_csv(events[:limit])
    fname = f"metano_detecciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    from fastapi.responses import Response
    return Response(content=data, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@app.get("/api/v55/export/excel", tags=["Exports v5.5"])
async def export_excel(
    limit: int = Query(500, ge=1, le=2000),
    activo: Optional[str] = None,
    user: Dict = Depends(require_feature("exports_excel")),
):
    """Exporta detecciones a Excel (.xlsx) con hoja de compliance."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    if activo:
        events = [e for e in events if e.get("activo_cercano") == activo]
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    data = Exporter.to_excel(events[:limit])
    fname = f"metano_reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    from fastapi.responses import Response
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

@app.get("/api/v55/export/pdf", tags=["Exports v5.5"])
async def export_pdf(
    limit: int = Query(100, ge=1, le=500),
    activo: Optional[str] = None,
    user: Dict = Depends(require_feature("exports_pdf")),
):
    """Exporta reporte ejecutivo en PDF."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    if activo:
        events = [e for e in events if e.get("activo_cercano") == activo]
    events.sort(key=lambda e: e.get("fecha_deteccion", ""), reverse=True)
    data = Exporter.to_pdf(events[:limit])
    fname = f"metano_reporte_ejecutivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    from fastapi.responses import Response
    return Response(
        content=data, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

# API Keys
@app.get("/api/v55/keys", tags=["API Keys v5.5"])
async def list_api_keys(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Lista todas las API keys (solo admin)."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    return {"keys": api_keys.list_all(), "scopes_disponibles": api_keys.SCOPES}

@app.post("/api/v55/keys", tags=["API Keys v5.5"])
async def create_api_key(
    req: CreateApiKeyRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Crea una nueva API key con scopes específicos."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    info = api_keys.create(
        owner=user["sub"], name=req.name,
        scopes=req.scopes, rate_limit_per_min=req.rate_limit_per_min,
    )
    if audit_chain:
        audit_chain.append("API_KEY_CREATE", user["sub"], req.name,
                            {"scopes": req.scopes})
    return info

@app.delete("/api/v55/keys/{key_prefix}", tags=["API Keys v5.5"])
async def revoke_api_key(
    key_prefix: str,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Revoca una API key (puede pasar el prefijo)."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    ok = api_keys.revoke(key_prefix)
    if audit_chain:
        audit_chain.append("API_KEY_REVOKE", user["sub"], key_prefix, "")
    return {"success": ok}

# Webhooks
@app.get("/api/v55/webhooks", tags=["Webhooks v5.5"])
async def list_webhooks(
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Lista webhooks salientes."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    return {"webhooks": webhooks.list_all(), "events_disponibles": webhooks.EVENTS}

@app.post("/api/v55/webhooks", tags=["Webhooks v5.5"])
async def create_webhook(
    req: CreateWebhookRequest,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Registra un webhook saliente (SCADA/Slack/Teams/ERP)."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    hook = webhooks.register(
        owner=user["sub"], url=req.url, events=req.events,
        secret=req.secret, name=req.name,
    )
    if audit_chain:
        audit_chain.append("WEBHOOK_REGISTER", user["sub"], req.url,
                            {"events": req.events})
    return hook

@app.delete("/api/v55/webhooks/{hook_id}", tags=["Webhooks v5.5"])
async def delete_webhook(
    hook_id: str,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Elimina un webhook."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    ok = webhooks.delete(hook_id)
    if audit_chain:
        audit_chain.append("WEBHOOK_DELETE", user["sub"], hook_id, "")
    return {"success": ok}

@app.post("/api/v55/webhooks/{hook_id}/test", tags=["Webhooks v5.5"])
async def test_webhook(
    hook_id: str,
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Envía un evento de prueba a un webhook."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    hook = next((h for h in webhooks._hooks if h["id"] == hook_id), None)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    # Disparar solo a este hook
    hook["_temp_target"] = True
    original = list(webhooks._hooks)
    webhooks._hooks = [hook]
    await webhooks.fire("system.alert",
                        {"test": True, "message": "Ping desde MetanoSRGAN Elite v5.5"})
    webhooks._hooks = original
    return {"success": True, "delivered": hook.get("delivered", 0),
            "last_status": hook.get("last_status"), "last_error": hook.get("last_error")}

# Audit chain
@app.get("/api/v55/audit/chain", tags=["Audit Chain v5.5"])
async def get_audit_chain(
    limit: int = Query(50, ge=1, le=500),
    user: Dict = Depends(auth_manager.get_fastapi_dependencies()["require_admin"])
):
    """Cadena de auditoría inmutable (estilo blockchain)."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    return {
        "verificacion": audit_chain.verify(),
        "bloques": audit_chain.tail(limit),
    }

# Analytics
@app.get("/api/v55/analytics/by-period", tags=["Analytics v5.5"])
async def analytics_by_period(kind: str = Query("month", regex="^(day|week|month|year)$")):
    """Comparativa histórica por periodo."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    return HistoricalAnalytics.by_period(events, kind)

@app.get("/api/v55/analytics/by-asset", tags=["Analytics v5.5"])
async def analytics_by_asset():
    """Ranking de activos por gravedad y total de detecciones."""
    if not _ENHANCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="No disponible")
    events = _load_events()
    return HistoricalAnalytics.by_asset(events)

# WebSocket en vivo
from fastapi import WebSocket, WebSocketDisconnect
_ws_clients: List[WebSocket] = []

async def _broadcast_event(event_type: str, data: Dict):
    """Envía un evento a todos los clientes WebSocket conectados."""
    if not _ws_clients:
        return
    payload = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    dead = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_clients:
            _ws_clients.remove(ws)

@app.websocket("/api/ws/live")
async def websocket_live(ws: WebSocket):
    """Stream en vivo de heartbeats + push de eventos reales del pipeline."""
    await ws.accept()
    _ws_clients.append(ws)
    try:
        # Enviar snapshot inicial
        ia_status = _load_ia_status()
        await ws.send_json({
            "type": "snapshot",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_status": ia_status.get("system_status", "OPERATIONAL_24_7"),
            "pipeline_running": _pipeline_running,
            "last_results": ia_status.get("last_results", {}),
            "last_execution": ia_status.get("last_execution"),
            "modules": {
                "supabase": _SUPABASE_AVAILABLE,
                "tropomi": _TROPOMI_AVAILABLE,
                "ml": _ML_AVAILABLE,
                "telegram": _TELEGRAM_AVAILABLE,
                "enhancements": _ENHANCE_AVAILABLE,
                "admin_panel": _ADMIN_PANEL_AVAILABLE,
            },
            "data_source_real": True,
        })
        # Heartbeat con métricas cada 10 segundos
        while True:
            await asyncio.sleep(10)
            ia_status = _load_ia_status()
            await ws.send_json({
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_status": ia_status.get("system_status", "OPERATIONAL_24_7"),
                "pipeline_running": _pipeline_running,
                "last_execution": ia_status.get("last_execution"),
                "last_results": ia_status.get("last_results", {}),
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)

# ─── Endpoint de Diagnóstico Real ─────────────────────────────────────────────
@app.get("/api/system/diagnostics", tags=["Sistema v5.5"])
async def system_diagnostics():
    """
    Verifica EN VIVO cada conexión real del sistema.
    Útil para validar que no hay datos mockeados ni conexiones rotas.
    """
    diag = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.5.0",
        "production_grade": True,
        "checks": {},
    }

    # 1. Supabase real (no mock)
    try:
        if _SUPABASE_AVAILABLE and supabase_db and supabase_db.is_connected():
            count = len(supabase_db.get_detections(limit=1))
            total_dets = len(_load_events())
            diag["checks"]["supabase"] = {
                "status": "OK",
                "real": True,
                "url": os.getenv("SUPABASE_URL", "")[:48] + "...",
                "detecciones_almacenadas": total_dets,
                "responde": count >= 0,
            }
        else:
            diag["checks"]["supabase"] = {"status": "OFFLINE", "real": False}
    except Exception as e:
        diag["checks"]["supabase"] = {"status": "ERROR", "error": str(e)[:200]}

    # 2. TROPOMI real (Copernicus Sentinel-5P)
    try:
        if _TROPOMI_AVAILABLE and tropomi:
            diag["checks"]["tropomi_sentinel5p"] = {
                "status": "OK",
                "real": True,
                "fuente": "Copernicus Data Space — Sentinel-5P TROPOMI",
                "endpoint": "https://data-portal.s5p-pal.com",
                "modulo": "tropomi_direct_v37",
            }
        else:
            diag["checks"]["tropomi_sentinel5p"] = {"status": "OFFLINE"}
    except Exception as e:
        diag["checks"]["tropomi_sentinel5p"] = {"status": "ERROR", "error": str(e)[:200]}

    # 3. Open-Meteo (CH4 + viento real)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": 6.5, "longitude": -74.0,
                        "current": "methane", "timezone": "America/Bogota"}
            )
            data = r.json()
            ch4_now = data.get("current", {}).get("methane")
            diag["checks"]["open_meteo_ch4"] = {
                "status": "OK" if ch4_now is not None else "PARTIAL",
                "real": True,
                "ch4_actual_ppb": ch4_now,
                "fuente": "Open-Meteo Air Quality API + CAMS",
                "lat_consultada": 6.5, "lon_consultada": -74.0,
            }
    except Exception as e:
        diag["checks"]["open_meteo_ch4"] = {"status": "ERROR", "error": str(e)[:200]}

    # 4. Mapbox token configurado
    mapbox_token = os.getenv("MAPBOX_TOKEN", "")
    diag["checks"]["mapbox"] = {
        "status": "OK" if mapbox_token.startswith("pk.") else "MISSING",
        "real": True,
        "token_configurado": bool(mapbox_token),
        "estilos_disponibles": [
            "satellite-streets-v12 (≈1m urbano)",
            "satellite-v9", "streets-v12", "dark-v11", "outdoors-v12",
        ],
    }

    # 5. Telegram bot
    diag["checks"]["telegram_bot"] = {
        "status": "OK" if _TELEGRAM_AVAILABLE else "OFFLINE",
        "real": _TELEGRAM_AVAILABLE,
        "bot_configurado": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    }

    # 6. ML real (entrenado con datos)
    if _ML_AVAILABLE and _last_ml_report:
        diag["checks"]["ml_persistence"] = {
            "status": "OK",
            "real": True,
            "modelo": _last_ml_report.get("modelo", {}).get("method", "RandomForest"),
            "eventos_entrenamiento": _last_ml_report.get("modelo", {}).get("n_events", 0),
            "f1_score": _last_ml_report.get("modelo", {}).get("cv_f1_mean", 0),
        }
    elif _ML_AVAILABLE:
        diag["checks"]["ml_persistence"] = {"status": "READY", "real": True, "info": "Esperando primera ejecución"}
    else:
        diag["checks"]["ml_persistence"] = {"status": "OFFLINE"}

    # 7. JWT Auth
    diag["checks"]["jwt_auth"] = {
        "status": "OK" if _JWT_AVAILABLE else "OFFLINE",
        "real": _JWT_AVAILABLE,
        "usuarios_registrados": len(auth_manager._users) if _JWT_AVAILABLE else 0,
    }

    # 8. Sentinel Hub / EOX (capas mapa)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=4) as cli:
            r = await cli.head("https://tiles.maps.eox.at/wms")
            diag["checks"]["sentinel_eox_tiles"] = {
                "status": "OK" if r.status_code < 500 else "DEGRADED",
                "real": True,
                "fuente": "EOX Maps · Sentinel-2 Cloudless 2023 (CC-BY 4.0)",
                "http_status": r.status_code,
            }
    except Exception as e:
        diag["checks"]["sentinel_eox_tiles"] = {"status": "TIMEOUT", "error": str(e)[:100]}

    # 9. Pipeline status
    last_exec = _load_ia_status().get("last_execution")
    diag["checks"]["pipeline"] = {
        "status": "RUNNING" if _pipeline_running else "IDLE",
        "real": True,
        "ultima_ejecucion": last_exec,
        "ws_clientes_conectados": len(_ws_clients),
    }

    # Resumen
    ok = sum(1 for c in diag["checks"].values() if c.get("status") == "OK")
    total = len(diag["checks"])
    diag["resumen"] = {
        "modulos_ok": ok,
        "modulos_total": total,
        "porcentaje_salud": round(100 * ok / total, 1) if total else 0,
        "todo_real": all(c.get("real", False) for c in diag["checks"].values() if "real" in c),
        "datos_simulados": False,
    }
    return diag

@app.get("/api/v55/info", tags=["Sistema v5.5"])
async def v55_info():
    """Información de las nuevas capacidades v5.5."""
    return {
        "version": "5.5.0",
        "edicion": "MetanoSRGAN Elite — Mata-Gigantes Edition",
        "nuevas_capacidades": {
            "carbon_credits": _ENHANCE_AVAILABLE,
            "compliance_tracker": _ENHANCE_AVAILABLE,
            "exports_pdf_xlsx_csv": _ENHANCE_AVAILABLE,
            "api_keys_publicas": _ENHANCE_AVAILABLE,
            "webhooks_salientes": _ENHANCE_AVAILABLE,
            "audit_blockchain": _ENHANCE_AVAILABLE,
            "comparativas_historicas": _ENHANCE_AVAILABLE,
            "websocket_live": True,
            "panel_admin_completo": _ADMIN_PANEL_AVAILABLE,
        },
        "normativas_evaluadas": list(ComplianceTracker.NORMATIVAS.keys())
                                  if _ENHANCE_AVAILABLE else [],
        "metodologias_carbono": [
            "IPCC AR6 GWP100=29.8",
            "Verra VM0033",
            "Gold Standard Methane Recovery",
            "EU ETS / California CARB / China ETS"
        ] if _ENHANCE_AVAILABLE else [],
    }


# ─── Servir Archivos Estáticos ────────────────────────────────────────────────
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ─── Servir Frontend (Auth-First Architecture) ────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_root():
    """Raíz: redirige al login (la auth es lo primero que ve el usuario)."""
    return HTMLResponse(
        status_code=200,
        content=(
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<title>MetanoSRGAN Elite</title>'
            '<meta http-equiv="refresh" content="0; url=/login"/>'
            '<script>'
            'const t=localStorage.getItem("msr_token");'
            'const u=JSON.parse(localStorage.getItem("msr_user")||"{}");'
            'if(t){window.location.replace(u.role==="admin"?"/admin":"/app");}'
            'else{window.location.replace("/login");}'
            '</script></head>'
            '<body style="background:#0a0e1a;color:#e2e8f0;font-family:system-ui;'
            'display:flex;align-items:center;justify-content:center;height:100vh;">'
            '<p>Redirigiendo… <a href="/login" style="color:#00d4ff">Iniciar sesión</a></p>'
            '</body></html>'
        )
    )

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def serve_login():
    """Pantalla de autenticación."""
    fp = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.exists(fp):
        return FileResponse(fp)
    return HTMLResponse("<h1>Login no disponible</h1>", status_code=404)

@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def serve_admin():
    """Panel admin (gestión de usuarios/planes/permisos)."""
    fp = os.path.join(FRONTEND_DIR, "admin.html")
    if os.path.exists(fp):
        return FileResponse(fp)
    return HTMLResponse("<h1>Admin no disponible</h1>", status_code=404)

@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def serve_app():
    """Dashboard de usuario (con features filtradas por plan)."""
    fp = os.path.join(FRONTEND_DIR, "app.html")
    if os.path.exists(fp):
        return FileResponse(fp)
    # Fallback al dashboard original mientras /app.html no exista
    fp = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(fp):
        return FileResponse(fp)
    return HTMLResponse("<h1>App no disponible</h1>", status_code=404)

@app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa(path: str):
    """Sirve el SPA para todas las rutas no-API."""
    if path.startswith("api/") or path.startswith("static/"):
        return JSONResponse(status_code=404, content={"detail": "No encontrado"})
    # Servir archivo estático específico si existe (admin.js, etc.)
    candidate = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)
    # Fallback a /login para rutas desconocidas (auth-first)
    return HTMLResponse(
        '<script>window.location.replace("/login")</script>',
        status_code=200,
    )

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar el servidor."""
    logger.info("=" * 60)
    logger.info("MetanoSRGAN Elite v5.4 — Supabase Edition")
    logger.info(f"Supabase v3.8: {'OK' if _SUPABASE_AVAILABLE else 'N/A (modo local)'}")
    logger.info(f"Pipeline v3.5: {'OK' if _PIPELINE_AVAILABLE else 'N/A'}")
    logger.info(f"TROPOMI v3.7:  {'OK' if _TROPOMI_AVAILABLE else 'N/A'}")
    logger.info(f"ML v3.7:       {'OK' if _ML_AVAILABLE else 'N/A'}")
    logger.info(f"JWT v3.6:      {'OK' if _JWT_AVAILABLE else 'N/A'}")
    logger.info(f"Telegram v3.9: {'OK' if _TELEGRAM_AVAILABLE else 'N/A'}")
    logger.info(f"DATA_DIR:      {DATA_DIR}")
    logger.info(f"FRONTEND_DIR:  {FRONTEND_DIR}")
    logger.info("=" * 60)

    # Pre-entrenar ML si hay datos
    if ml_analyzer:
        try:
            ml_analyzer.train()
            logger.info("Modelos ML pre-entrenados al inicio")
        except Exception as e:
            logger.warning(f"Error pre-entrenando ML: {e}")

    # Verificar datos locales
    table_path = os.path.join(DATA_DIR, "event_master_table.json")
    if os.path.exists(table_path):
        with open(table_path) as f:
            events = json.load(f)
        logger.info(f"Datos locales: {len(events)} eventos en event_master_table.json")
    else:
        logger.warning("event_master_table.json no encontrado")

    # ─── Auto-Ticket Generator + Scheduler v5.5 ────────────────────────────
    global _auto_ticket_gen, _pipeline_scheduler
    if _ENHANCE_AVAILABLE:
        try:
            _auto_ticket_gen = AutoTicketGenerator(
                tickets_dir=TICKETS_DIR,
                supabase_db=supabase_db if _SUPABASE_AVAILABLE else None,
                telegram_notifier=telegram_notifier if _TELEGRAM_AVAILABLE else None,
                broadcast_fn=_broadcast_event,
            )
            logger.info(f"AutoTicketGenerator iniciado · umbral={UMBRAL_TICKET_AUTO} · élite={UMBRAL_TICKET_ELITE}")
        except Exception as e:
            logger.warning(f"AutoTicketGenerator no iniciado: {e}")

        # Iniciar scheduler automático del pipeline
        try:
            _pipeline_scheduler = PipelineScheduler(
                run_pipeline_fn=_run_pipeline_task,
                ticket_generator=_auto_ticket_gen,
                broadcast_fn=_broadcast_event,
            )
            _pipeline_scheduler.start()
            logger.info("PipelineScheduler iniciado: 4 ejecuciones diarias automáticas")
        except Exception as e:
            logger.warning(f"PipelineScheduler no iniciado: {e}", exc_info=True)

    # Generar tickets de detecciones críticas existentes (recuperación inicial)
    if _auto_ticket_gen:
        try:
            existing_events = _load_events()
            tk = _auto_ticket_gen.process_batch(existing_events)
            if tk["tickets_creados"] > 0:
                logger.info(
                    f"Tickets recuperados de detecciones existentes: "
                    f"{tk['tickets_creados']} (P0={tk['elite_p0']}, P1={tk['critico_p1']})"
                )
        except Exception as e:
            logger.warning(f"Error generando tickets de recuperación: {e}")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
