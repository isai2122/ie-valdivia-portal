"""
integration_v36.py — MetanoSRGAN Elite v3.6
Módulo de integración principal que une todos los nuevos componentes v3.6:

  1. NetCDF Sentinel-5P    → netcdf_sentinel5p_v36.py
  2. SRGAN Super-Resolución → srgan_superresolution_v36.py
  3. Notificaciones         → notification_engine_v36.py
  4. MongoDB Persistencia   → mongodb_persistence_v36.py
  5. JWT Autenticación      → jwt_auth_v36.py
  6. App Móvil EliteField   → mobile/EliteField/

Este módulo extiende el pipeline v3.5 con las capacidades v3.6.
Se integra con detection_pipeline_v35.py y api_server_v35.py.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ─── Importaciones de módulos v3.6 ────────────────────────────────────────────
try:
    from mongodb_persistence_v36 import MongoDBPersistence
    _MONGO_AVAILABLE = True
except ImportError:
    _MONGO_AVAILABLE = False
    logger.warning("MongoDB module not available")

try:
    from jwt_auth_v36 import JWTAuthManager, auth_manager
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False
    logger.warning("JWT module not available")

try:
    from notification_engine_v36 import NotificationEngine
    _NOTIFICATIONS_AVAILABLE = True
except ImportError:
    _NOTIFICATIONS_AVAILABLE = False
    logger.warning("Notification engine not available")

try:
    from netcdf_sentinel5p_v36 import NetCDFSentinel5PDownloader
    _NETCDF_AVAILABLE = True
except ImportError:
    _NETCDF_AVAILABLE = False
    logger.warning("NetCDF Sentinel-5P module not available")

try:
    from srgan_superresolution_v36 import SRGANSuperResolution
    _SRGAN_AVAILABLE = True
except ImportError:
    _SRGAN_AVAILABLE = False
    logger.warning("SRGAN module not available")


class MetanoSRGANv36Integration:
    """
    Integración completa de MetanoSRGAN Elite v3.6.
    Orquesta todos los módulos nuevos sobre el pipeline v3.5 existente.
    """

    def __init__(self):
        self.version = "3.6"
        self._init_modules()

    def _init_modules(self):
        """Inicializa todos los módulos disponibles."""
        # MongoDB
        self.db = MongoDBPersistence() if _MONGO_AVAILABLE else None

        # JWT Auth
        self.auth = auth_manager if _JWT_AVAILABLE else None

        # Notificaciones
        self.notifier = NotificationEngine() if _NOTIFICATIONS_AVAILABLE else None

        # NetCDF Sentinel-5P
        self.netcdf = NetCDFSentinel5PDownloader() if _NETCDF_AVAILABLE else None

        # SRGAN
        self.srgan = SRGANSuperResolution() if _SRGAN_AVAILABLE else None

        logger.info(
            f"MetanoSRGAN v3.6 inicializado — "
            f"MongoDB: {'OK' if self.db else 'N/A'} | "
            f"JWT: {'OK' if self.auth else 'N/A'} | "
            f"Notif: {'OK' if self.notifier else 'N/A'} | "
            f"NetCDF: {'OK' if self.netcdf else 'N/A'} | "
            f"SRGAN: {'OK' if self.srgan else 'N/A'}"
        )

    # ─── Pipeline Completo v3.6 ───────────────────────────────────────────────
    def run_full_pipeline_v36(
        self,
        detections: List[Dict],
        apply_srgan: bool = True,
        notify: bool = True,
        persist: bool = True,
    ) -> Dict:
        """
        Ejecuta el pipeline completo v3.6 sobre una lista de detecciones.

        Flujo:
          1. Aplicar SRGAN a detecciones con Elite Score ≥ 60
          2. Persistir todas las detecciones en MongoDB
          3. Enviar notificaciones para Elite Score ≥ 80
          4. Retornar resumen del ciclo

        Args:
            detections: Lista de detecciones del pipeline v3.5
            apply_srgan: Si aplicar super-resolución
            notify: Si enviar notificaciones
            persist: Si persistir en MongoDB

        Returns:
            Diccionario con resultados del ciclo v3.6
        """
        results = {
            "version": "3.6",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_detections": len(detections),
            "srgan_applied": 0,
            "notifications_sent": 0,
            "persisted": 0,
            "elite_alerts": [],
            "errors": [],
        }

        if not detections:
            logger.info("v3.6 pipeline: sin detecciones para procesar.")
            return results

        # ── 1. Super-Resolución SRGAN ─────────────────────────────────────────
        enhanced_detections = []
        if apply_srgan and self.srgan:
            for det in detections:
                try:
                    if det.get("elite_score", 0) >= 60:
                        enhanced = self._apply_srgan_to_detection(det)
                        enhanced_detections.append(enhanced)
                        if enhanced.get("sr_applied"):
                            results["srgan_applied"] += 1
                    else:
                        enhanced_detections.append(det)
                except Exception as e:
                    logger.error(f"SRGAN error en {det.get('nombre', '?')}: {e}")
                    enhanced_detections.append(det)
                    results["errors"].append(f"SRGAN: {e}")
        else:
            enhanced_detections = detections

        # ── 2. Persistencia MongoDB ───────────────────────────────────────────
        if persist and self.db:
            try:
                count = self.db.insert_many_detections(enhanced_detections)
                results["persisted"] = count
                logger.info(f"v3.6: {count} detecciones persistidas en MongoDB.")
            except Exception as e:
                logger.error(f"MongoDB persist error: {e}")
                results["errors"].append(f"MongoDB: {e}")

        # ── 3. Notificaciones Elite ───────────────────────────────────────────
        if notify and self.notifier:
            elite = [d for d in enhanced_detections if d.get("elite_score", 0) >= 80]
            if elite:
                try:
                    notif_result = self.notifier.notify_elite_alerts(elite)
                    results["notifications_sent"] = notif_result.get("sent", 0)
                    results["elite_alerts"] = [
                        {
                            "nombre": d.get("nombre"),
                            "elite_score": d.get("elite_score"),
                            "ch4_ppb_anomaly": d.get("ch4_ppb_anomaly"),
                            "perdida_usd_dia": d.get("perdida_usd_dia"),
                        }
                        for d in elite
                    ]
                    logger.info(
                        f"v3.6: {results['notifications_sent']} notificaciones enviadas "
                        f"para {len(elite)} alertas Elite."
                    )
                except Exception as e:
                    logger.error(f"Notification error: {e}")
                    results["errors"].append(f"Notificaciones: {e}")

        # ── 4. Guardar estado del sistema ─────────────────────────────────────
        if persist and self.db:
            try:
                self.db.save_system_status({
                    "version": "3.6",
                    "cycle_results": results,
                    "modules": self.get_modules_status(),
                })
            except Exception as e:
                logger.warning(f"Error guardando estado del sistema: {e}")

        return results

    def _apply_srgan_to_detection(self, detection: Dict) -> Dict:
        """Aplica SRGAN a una detección individual."""
        if not self.srgan:
            return detection

        try:
            # Crear array simulado de concentración CH4
            import numpy as np
            lat, lon = detection.get("lat", 7.0), detection.get("lon", -73.5)
            ch4_value = detection.get("ch4_ppb_total", 1850)

            # Grid 16x16 centrado en el activo (resolución 5.5km)
            grid_size = 16
            grid = np.full((grid_size, grid_size), ch4_value, dtype=np.float32)
            # Agregar gradiente realista
            center = grid_size // 2
            for i in range(grid_size):
                for j in range(grid_size):
                    dist = ((i - center) ** 2 + (j - center) ** 2) ** 0.5
                    anomaly = detection.get("ch4_ppb_anomaly", 0) * max(0, 1 - dist / (grid_size / 2))
                    grid[i, j] += anomaly

            # Aplicar super-resolución
            sr_result = self.srgan.upscale_ch4_grid(
                grid,
                lat_center=lat,
                lon_center=lon,
                asset_name=detection.get("nombre", "unknown"),
            )

            if sr_result.get("success"):
                enhanced = detection.copy()
                enhanced["sr_applied"] = True
                enhanced["sr_resolution_m"] = sr_result.get("output_resolution_m", 10)
                enhanced["sr_scale_factor"] = sr_result.get("scale_factor", 550)
                enhanced["sr_ch4_peak_ppb"] = float(sr_result.get("peak_value", ch4_value))
                enhanced["sr_confidence"] = sr_result.get("confidence", 0.85)
                return enhanced

        except Exception as e:
            logger.warning(f"SRGAN apply error: {e}")

        return detection

    # ─── Integración con API Server v3.5 ──────────────────────────────────────
    def get_fastapi_router(self):
        """
        Retorna un router FastAPI con todos los endpoints v3.6.
        Se monta en el api_server_v35.py existente.

        Uso en api_server_v35.py:
            from integration_v36 import v36
            app.include_router(v36.get_fastapi_router(), prefix="/api/v36")
        """
        try:
            from fastapi import APIRouter, Depends, HTTPException
            from pydantic import BaseModel

            router = APIRouter(tags=["v3.6"])
            auth_deps = self.auth.get_fastapi_dependencies() if self.auth else {}
            require_auth = auth_deps.get("require_auth")

            # ── Auth endpoints ────────────────────────────────────────────────
            class LoginRequest(BaseModel):
                username: str
                password: str

            @router.post("/auth/login")
            async def login(req: LoginRequest):
                if not self.auth:
                    raise HTTPException(503, "Auth service not available")
                success, token_data, message = self.auth.login(req.username, req.password)
                if not success:
                    raise HTTPException(401, message)
                return token_data

            @router.post("/auth/logout")
            async def logout(body: dict):
                if self.auth:
                    self.auth.logout(
                        body.get("access_token", ""),
                        body.get("refresh_token"),
                    )
                return {"message": "Sesión cerrada"}

            @router.post("/auth/refresh")
            async def refresh_token(body: dict):
                if not self.auth:
                    raise HTTPException(503, "Auth service not available")
                success, new_token, message = self.auth.refresh_access_token(
                    body.get("refresh_token", "")
                )
                if not success:
                    raise HTTPException(401, message)
                return {"access_token": new_token}

            # ── Detection endpoints ───────────────────────────────────────────
            @router.get("/detections/latest")
            async def get_latest_detections(limit: int = 20):
                if not self.db:
                    raise HTTPException(503, "Database not available")
                return self.db.get_detections(limit=limit)

            @router.get("/detections/elite")
            async def get_elite_detections(threshold: float = 80.0):
                if not self.db:
                    raise HTTPException(503, "Database not available")
                return self.db.get_elite_alerts(threshold=threshold)

            @router.get("/detections/asset/{nombre}")
            async def get_asset_detections(nombre: str, days_back: int = 30):
                if not self.db:
                    raise HTTPException(503, "Database not available")
                return self.db.get_detections(nombre=nombre, days_back=days_back)

            # ── Stats endpoint ────────────────────────────────────────────────
            @router.get("/stats")
            async def get_stats(days_back: int = 30):
                if not self.db:
                    raise HTTPException(503, "Database not available")
                return self.db.get_statistics(days_back=days_back)

            # ── Tickets endpoints ─────────────────────────────────────────────
            @router.get("/tickets")
            async def get_tickets(status: Optional[str] = None):
                if not self.db:
                    raise HTTPException(503, "Database not available")
                return self.db.get_detections(limit=50)  # Placeholder

            # ── Modules status ────────────────────────────────────────────────
            @router.get("/modules/status")
            async def get_modules_status():
                return self.get_modules_status()

            return router

        except ImportError:
            logger.warning("FastAPI no disponible. Router v3.6 no creado.")
            return None

    # ─── Estado del sistema ───────────────────────────────────────────────────
    def get_modules_status(self) -> Dict:
        """Retorna el estado de todos los módulos v3.6."""
        status = {
            "version": "3.6",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modules": {
                "netcdf_sentinel5p": {
                    "available": _NETCDF_AVAILABLE,
                    "status": self.netcdf.get_status() if self.netcdf else None,
                },
                "srgan_superresolution": {
                    "available": _SRGAN_AVAILABLE,
                    "status": self.srgan.get_status() if self.srgan else None,
                },
                "notification_engine": {
                    "available": _NOTIFICATIONS_AVAILABLE,
                    "status": self.notifier.get_status() if self.notifier else None,
                },
                "mongodb_persistence": {
                    "available": _MONGO_AVAILABLE,
                    "status": self.db.get_status() if self.db else None,
                },
                "jwt_auth": {
                    "available": _JWT_AVAILABLE,
                    "status": self.auth.get_status() if self.auth else None,
                },
                "mobile_app": {
                    "available": True,
                    "platform": "React Native / Expo",
                    "screens": ["Login", "Dashboard", "Map", "Tickets", "Alerts", "Profile"],
                    "path": "mobile/EliteField/",
                },
            },
        }
        return status

    def print_status_report(self):
        """Imprime un reporte de estado formateado."""
        status = self.get_modules_status()
        print("\n" + "=" * 60)
        print(f"  MetanoSRGAN Elite v{self.version} — Estado de Módulos")
        print("=" * 60)
        for name, info in status["modules"].items():
            avail = "OK" if info["available"] else "N/A"
            print(f"  {name:<30} [{avail}]")
        print("=" * 60 + "\n")


# ─── Instancia global ─────────────────────────────────────────────────────────
v36 = MetanoSRGANv36Integration()

if __name__ == "__main__":
    v36.print_status_report()
