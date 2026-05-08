"""
supabase_integration_v38.py — MetanoSRGAN Elite v3.8
Integración real con Supabase para persistencia en la nube.
Tablas: detecciones, usuarios, logs, tickets, ml_predictions
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseDB:
    """Cliente de Supabase para persistencia en la nube."""
    
    def __init__(self):
        """Inicializa la conexión a Supabase."""
        self.url = os.getenv("SUPABASE_URL")
        # Usar SERVICE_ROLE_KEY si está disponible, de lo contrario ANON_KEY
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        # Schema discovery cache (descubierto al primer uso)
        self._detections_columns: Optional[set] = None
        self._tickets_columns: Optional[set] = None
        # Columnas que sabemos NO existen (aprendidas de errores PGRST204)
        self._invalid_detections_cols: set = set()
        self._invalid_tickets_cols: set = set()

        if not self.url or not self.key:
            logger.warning("Credenciales de Supabase no configuradas. Usando modo local.")
            self.client: Optional[Client] = None
        else:
            try:
                # Limpiar posibles espacios o comillas en las claves
                self.url = self.url.strip().strip('"').strip("'")
                self.key = self.key.strip().strip('"').strip("'")
                self.client = create_client(self.url, self.key)
                logger.info("✓ Conexión a Supabase establecida")
                # Descubrir schema real al inicio
                self._discover_schemas()
            except Exception as e:
                logger.error(f"Error conectando a Supabase: {e}")
                self.client = None

    def _discover_schemas(self):
        """Descubre las columnas reales de las tablas leyendo una fila ejemplo."""
        try:
            r = self.client.table("detecciones").select("*").limit(1).execute()
            if r.data:
                self._detections_columns = set(r.data[0].keys())
                logger.info(f"Schema 'detecciones' descubierto: {len(self._detections_columns)} columnas")
        except Exception as e:
            logger.warning(f"No se pudo descubrir schema 'detecciones': {e}")
        try:
            r = self.client.table("tickets").select("*").limit(1).execute()
            if r.data:
                self._tickets_columns = set(r.data[0].keys())
                logger.info(f"Schema 'tickets' descubierto: {len(self._tickets_columns)} columnas")
        except Exception as e:
            logger.warning(f"No se pudo descubrir schema 'tickets': {e}")
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a Supabase."""
        return self.client is not None
    
    # ─── Detecciones ──────────────────────────────────────────────────────────
    
    # Columnas core que existen en la tabla `detecciones` (schema v5.4 en Supabase).
    # Cualquier columna nueva que añadan otros módulos (ej. certificacion_espectral
    # de TROPOMI Sentinel-2 SWIR) se filtra para no romper el insert.
    _DETECTIONS_CORE_COLUMNS = {
        "id", "fecha_deteccion", "activo_cercano", "operador", "tipo_activo",
        "latitud", "longitud", "intensidad_ppb", "ch4_ppb_total",
        "ch4_ppb_anomaly", "score_prioridad", "elite_score", "categoria_alerta",
        "perdida_economica_usd_dia", "viento_dominante_velocidad",
        "viento_dominante_direccion", "persistencia_dias", "flujo_kgh",
        "area_pluma_km2", "fuente_datos", "calidad_dato",
    }

    def insert_detection(self, detection: Dict[str, Any]) -> Optional[Dict]:
        """Inserta una detección filtrando a las columnas reales del schema."""
        if not self.client:
            logger.warning("Supabase no disponible. Detección no guardada en nube.")
            return None

        try:
            # Schema descubierto al iniciar (real, no asumido).
            allowed = self._detections_columns or self._DETECTIONS_CORE_COLUMNS
            payload = {k: v for k, v in detection.items() if k in allowed}

            if "fecha_deteccion" not in payload and "fecha_deteccion" in allowed:
                payload["fecha_deteccion"] = datetime.now(timezone.utc).isoformat()

            try:
                response = self.client.table("detecciones").insert(payload).execute()
                logger.info(f"✓ Detección insertada en Supabase: {payload.get('activo_cercano')}")
                return response.data[0] if response.data else None
            except Exception as ee:
                # Reintento adaptativo iterativo: ir quitando columnas problemáticas
                err = str(ee)
                import re as _re
                attempts = 0
                while attempts < 5:
                    m = _re.search(r"Could not find the '(\w+)' column", err)
                    if not m:
                        break
                    bad = m.group(1)
                    if bad not in payload:
                        break
                    payload.pop(bad, None)
                    attempts += 1
                    try:
                        response = self.client.table("detecciones").insert(payload).execute()
                        logger.info(f"✓ Detección insertada (omitidas {attempts} cols): {payload.get('activo_cercano')}")
                        # Cachear schema corregido
                        if self._detections_columns is not None:
                            self._detections_columns.discard(bad)
                        return response.data[0] if response.data else None
                    except Exception as e2:
                        err = str(e2)
                logger.error(f"Error insertando detección tras {attempts} reintentos: {err[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error insertando detección en Supabase: {e}")
            return None
    
    def get_detections(self, limit: int = 100, activo: Optional[str] = None) -> List[Dict]:
        """Obtiene detecciones de Supabase."""
        if not self.client:
            return []
        
        try:
            query = self.client.table("detecciones").select("*").order("fecha_deteccion", desc=True).limit(limit)
            
            if activo:
                query = query.eq("activo_cercano", activo)
            
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo detecciones de Supabase: {e}")
            return []
    
    def get_latest_detection(self, activo: str) -> Optional[Dict]:
        """Obtiene la detección más reciente de un activo."""
        if not self.client:
            return None
        
        try:
            response = (
                self.client.table("detecciones")
                .select("*")
                .eq("activo_cercano", activo)
                .order("fecha_deteccion", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error obteniendo última detección: {e}")
            return None
    
    # ─── Tickets ──────────────────────────────────────────────────────────────
    
    # Columnas existentes en la tabla `tickets` de Supabase (schema v5.4 conservador).
    # NOTA: la tabla puede no tener fecha_deteccion u otras — el discovery automático
    # las corrige al primer uso si la tabla está vacía.
    _TICKETS_CORE_COLUMNS = {
        "ticket_id", "estado", "fuente", "categoria", "prioridad",
        "creado_en", "activo", "operador", "tipo_activo",
        "latitud", "longitud", "ch4_ppb", "ch4_anomaly_ppb",
        "score", "perdida_usd_dia", "asignado_a", "fecha_creacion",
    }

    def insert_ticket(self, ticket: Dict[str, Any]) -> Optional[Dict]:
        """Inserta un ticket filtrando a las columnas reales del schema.

        En v5.5 los tickets son persistidos primero en JSON local (fuente de verdad).
        Supabase es persistencia secundaria opcional. Si la tabla legacy v5.4 no es
        compatible con el schema v5.5 (tipos diferentes), se loguea una sola vez
        y se silencia para no contaminar logs.
        """
        if not self.client:
            return None
        if getattr(self, "_tickets_supabase_disabled", False):
            return None

        try:
            allowed = self._tickets_columns or self._TICKETS_CORE_COLUMNS
            payload = {
                k: v for k, v in ticket.items()
                if k in allowed and k not in self._invalid_tickets_cols
            }
            # Coerciones para schema v5.4 legacy:
            # prioridad puede ser INT en algunos schemas
            if "prioridad" in payload and isinstance(payload["prioridad"], str):
                pmap = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
                payload["prioridad_num"] = pmap.get(payload["prioridad"], 1)

            if "fecha_creacion" not in payload and "fecha_creacion" in allowed \
                    and "fecha_creacion" not in self._invalid_tickets_cols:
                payload["fecha_creacion"] = datetime.now(timezone.utc).isoformat()

            import re as _re
            for attempt in range(8):
                try:
                    response = self.client.table("tickets").insert(payload).execute()
                    return response.data[0] if response.data else None
                except Exception as ee:
                    err = str(ee)
                    m = _re.search(r"Could not find the '(\w+)' column", err)
                    if m:
                        bad = m.group(1)
                        self._invalid_tickets_cols.add(bad)
                        if bad in payload:
                            del payload[bad]
                            continue
                    # Error de tipo / constraint → schema legacy incompatible.
                    if "invalid input syntax" in err or "violates" in err or "23502" in err:
                        if not getattr(self, "_tickets_supabase_disabled", False):
                            logger.warning(
                                "Tabla 'tickets' de Supabase tiene schema legacy v5.4 "
                                "incompatible con v5.5. Tickets se persisten solo en "
                                "JSON local. Para activar Supabase, recrear la tabla. "
                                f"Error: {err[:120]}"
                            )
                            self._tickets_supabase_disabled = True
                        return None
                    logger.warning(f"Error inserción ticket Supabase: {err[:150]}")
                    return None
            return None
        except Exception as e:
            logger.warning(f"Error creando ticket en Supabase: {e}")
            return None

    def update_ticket(self, ticket_id: str, ticket: Dict[str, Any]) -> Optional[Dict]:
        """Actualiza un ticket existente (solo columnas existentes)."""
        if not self.client:
            return None
        try:
            payload = {k: v for k, v in ticket.items() if k in self._TICKETS_CORE_COLUMNS}
            response = (
                self.client.table("tickets")
                .update(payload)
                .eq("ticket_id", ticket_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.warning(f"Error actualizando ticket Supabase: {e}")
            return None
    
    def get_tickets(self, limit: int = 50) -> List[Dict]:
        """Obtiene tickets de Supabase."""
        if not self.client:
            return []
        
        try:
            response = (
                self.client.table("tickets")
                .select("*")
                .order("fecha_creacion", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo tickets: {e}")
            return []
    
    # ─── Predicciones ML ──────────────────────────────────────────────────────
    
    def insert_ml_prediction(self, prediction: Dict[str, Any]) -> Optional[Dict]:
        """Inserta una predicción ML."""
        if not self.client:
            return None
        
        try:
            if "timestamp" not in prediction:
                prediction["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            response = self.client.table("ml_predictions").insert(prediction).execute()
            logger.info(f"Predicción ML guardada: {prediction.get('activo')}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error guardando predicción ML: {e}")
            return None
    
    def get_ml_predictions(self, activo: Optional[str] = None) -> List[Dict]:
        """Obtiene predicciones ML."""
        if not self.client:
            return []
        
        try:
            query = self.client.table("ml_predictions").select("*").order("timestamp", desc=True).limit(100)
            
            if activo:
                query = query.eq("activo", activo)
            
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo predicciones ML: {e}")
            return []
    
    # ─── Logs del Sistema ─────────────────────────────────────────────────────
    
    def insert_log(self, log_entry: Dict[str, Any]) -> Optional[Dict]:
        """Inserta un log del sistema."""
        if not self.client:
            return None
        
        try:
            if "timestamp" not in log_entry:
                log_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            response = self.client.table("system_logs").insert(log_entry).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error insertando log: {e}")
            return None
    
    def get_logs(self, limit: int = 1000) -> List[Dict]:
        """Obtiene logs del sistema."""
        if not self.client:
            return []
        
        try:
            response = (
                self.client.table("system_logs")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error obteniendo logs: {e}")
            return []
    
    # ─── Estadísticas ────────────────────────────────────────────────────────
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema desde Supabase."""
        if not self.client:
            return {}
        
        try:
            stats = {
                "total_detecciones": 0,
                "total_tickets": 0,
                "activos_unicos": 0,
                "elite_score_maximo": 0,
                "perdida_total_usd": 0,
                "impacto_co2e_total": 0,
            }
            
            # Total de detecciones
            det_resp = self.client.table("detecciones").select("count", count="exact").execute()
            stats["total_detecciones"] = det_resp.count or 0
            
            # Total de tickets
            tick_resp = self.client.table("tickets").select("count", count="exact").execute()
            stats["total_tickets"] = tick_resp.count or 0
            
            # Activos únicos
            activos_resp = self.client.table("detecciones").select("activo_cercano", count="exact").execute()
            if activos_resp.data:
                stats["activos_unicos"] = len(set(d.get("activo_cercano") for d in activos_resp.data if d.get("activo_cercano")))
            
            logger.info(f"Estadísticas obtenidas: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}


# Instancia global
db = SupabaseDB()


if __name__ == "__main__":
    # Test de conexión
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("MetanoSRGAN Elite v3.8 — Supabase Integration Test")
    print("=" * 60)
    
    if db.is_connected():
        print("✓ Conectado a Supabase")
        
        # Test: Obtener estadísticas
        stats = db.get_statistics()
        print(f"\nEstadísticas del sistema:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        
        # Test: Obtener últimas detecciones
        dets = db.get_detections(limit=3)
        print(f"\nÚltimas 3 detecciones en Supabase:")
        for d in dets:
            print(f"  - {d.get('activo_cercano')}: {d.get('fecha_deteccion')}")
    else:
        print("✗ No conectado a Supabase")
