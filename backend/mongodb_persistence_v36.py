"""
mongodb_persistence_v36.py — MetanoSRGAN Elite v3.6
Base de datos MongoDB para historial persistente en producción.

Colecciones:
  - detections:      Todas las detecciones certificadas (historial completo)
  - events:          Tabla maestra de eventos (equivale a event_master_table.json)
  - tickets:         Tickets de intervención generados
  - notifications:   Log de notificaciones enviadas
  - system_status:   Estado del sistema (snapshots cada ciclo)
  - srgan_results:   Resultados de super-resolución

Configuración vía variables de entorno:
  MONGODB_URI         — URI de conexión (ej: mongodb://localhost:27017)
  MONGODB_DB_NAME     — Nombre de la base de datos (default: metanosrgan_elite)

Fallback: Si MongoDB no está disponible, usa archivos JSON locales
(compatibilidad con v3.5).
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Configuración ────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "metanosrgan_elite")
DATA_DIR = os.getenv("DATA_DIR", "/home/ubuntu/metanosrgan_v36/data")

# Colecciones
COL_DETECTIONS = "detections"
COL_EVENTS = "events"
COL_TICKETS = "tickets"
COL_NOTIFICATIONS = "notifications"
COL_SYSTEM_STATUS = "system_status"
COL_SRGAN_RESULTS = "srgan_results"


def _check_pymongo() -> bool:
    try:
        import pymongo
        return True
    except ImportError:
        return False


class MongoDBPersistence:
    """
    Capa de persistencia MongoDB para MetanoSRGAN Elite.
    Provee fallback automático a JSON local si MongoDB no está disponible.
    """

    def __init__(
        self,
        uri: str = MONGODB_URI,
        db_name: str = MONGODB_DB_NAME,
        data_dir: str = DATA_DIR,
    ):
        self.uri = uri
        self.db_name = db_name
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._pymongo_available = _check_pymongo()
        self._client = None
        self._db = None
        self._connected = False

        if self._pymongo_available:
            self._connect()

    # ─── Conexión ─────────────────────────────────────────────────────────────
    def _connect(self) -> bool:
        """Intenta conectar a MongoDB."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            # Verificar conexión
            self._client.admin.command("ping")
            self._db = self._client[self.db_name]
            self._connected = True
            self._ensure_indexes()
            logger.info(f"MongoDB conectado: {self.uri} / {self.db_name}")
            return True
        except Exception as e:
            logger.warning(
                f"MongoDB no disponible ({e}). "
                "Usando fallback JSON local."
            )
            self._connected = False
            return False

    def _ensure_indexes(self):
        """Crea índices para optimizar consultas frecuentes."""
        try:
            # detections: índice por nombre, timestamp y elite_score
            self._db[COL_DETECTIONS].create_index([("nombre", 1), ("timestamp", -1)])
            self._db[COL_DETECTIONS].create_index([("elite_score", -1)])
            self._db[COL_DETECTIONS].create_index([("timestamp", -1)])

            # events: índice por nombre y fecha
            self._db[COL_EVENTS].create_index([("nombre", 1), ("fecha", -1)])

            # tickets: índice por estado y fecha
            self._db[COL_TICKETS].create_index([("estado", 1), ("fecha_creacion", -1)])

            # notifications: índice por timestamp
            self._db[COL_NOTIFICATIONS].create_index([("timestamp", -1)])

            # system_status: TTL index (mantener solo 30 días)
            self._db[COL_SYSTEM_STATUS].create_index(
                [("timestamp", 1)],
                expireAfterSeconds=30 * 24 * 3600,
            )
            logger.info("MongoDB: índices creados/verificados.")
        except Exception as e:
            logger.warning(f"MongoDB: error creando índices: {e}")

    def is_connected(self) -> bool:
        """Verifica si la conexión MongoDB está activa."""
        if not self._connected or not self._client:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            self._connected = False
            return False

    # ─── Operaciones CRUD ─────────────────────────────────────────────────────
    def insert_detection(self, detection: Dict) -> Optional[str]:
        """
        Inserta una detección certificada en la base de datos.

        Args:
            detection: Diccionario con datos de la detección.

        Returns:
            ID del documento insertado, o None si falló.
        """
        detection = detection.copy()
        detection.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        detection.setdefault("version", "3.6")

        if self.is_connected():
            try:
                result = self._db[COL_DETECTIONS].insert_one(detection)
                doc_id = str(result.inserted_id)
                logger.debug(f"MongoDB: detección insertada {doc_id}")
                return doc_id
            except Exception as e:
                logger.error(f"MongoDB insert_detection error: {e}")

        # Fallback JSON
        return self._json_append(COL_DETECTIONS, detection)

    def insert_many_detections(self, detections: List[Dict]) -> int:
        """Inserta múltiples detecciones en batch."""
        if not detections:
            return 0

        docs = []
        for d in detections:
            doc = d.copy()
            doc.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            doc.setdefault("version", "3.6")
            docs.append(doc)

        if self.is_connected():
            try:
                result = self._db[COL_DETECTIONS].insert_many(docs)
                count = len(result.inserted_ids)
                logger.info(f"MongoDB: {count} detecciones insertadas en batch.")
                return count
            except Exception as e:
                logger.error(f"MongoDB insert_many error: {e}")

        # Fallback JSON
        for doc in docs:
            self._json_append(COL_DETECTIONS, doc)
        return len(docs)

    def get_detections(
        self,
        nombre: Optional[str] = None,
        days_back: int = 30,
        min_score: float = 0.0,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Consulta detecciones históricas con filtros.

        Args:
            nombre: Filtrar por nombre de activo.
            days_back: Cuántos días hacia atrás consultar.
            min_score: Elite Score mínimo.
            limit: Máximo de resultados.

        Returns:
            Lista de detecciones ordenadas por timestamp descendente.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

        if self.is_connected():
            try:
                query: Dict[str, Any] = {"timestamp": {"$gte": cutoff}}
                if nombre:
                    query["nombre"] = nombre
                if min_score > 0:
                    query["elite_score"] = {"$gte": min_score}

                cursor = (
                    self._db[COL_DETECTIONS]
                    .find(query, {"_id": 0})
                    .sort("timestamp", -1)
                    .limit(limit)
                )
                return list(cursor)
            except Exception as e:
                logger.error(f"MongoDB get_detections error: {e}")

        # Fallback JSON
        return self._json_query(COL_DETECTIONS, nombre=nombre, days_back=days_back, limit=limit)

    def get_elite_alerts(self, threshold: float = 80.0, days_back: int = 7) -> List[Dict]:
        """Retorna detecciones con Elite Score ≥ threshold en los últimos N días."""
        return self.get_detections(min_score=threshold, days_back=days_back)

    def insert_ticket(self, ticket: Dict) -> Optional[str]:
        """Inserta un ticket de intervención."""
        ticket = ticket.copy()
        ticket.setdefault("fecha_creacion", datetime.now(timezone.utc).isoformat())
        ticket.setdefault("estado", "PENDIENTE")
        ticket.setdefault("version", "3.6")

        if self.is_connected():
            try:
                result = self._db[COL_TICKETS].insert_one(ticket)
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"MongoDB insert_ticket error: {e}")

        return self._json_append(COL_TICKETS, ticket)

    def update_ticket_status(self, ticket_id: str, status: str, notes: str = "") -> bool:
        """Actualiza el estado de un ticket (PENDIENTE → EN_CAMPO → CERRADO)."""
        if self.is_connected():
            try:
                from bson import ObjectId
                result = self._db[COL_TICKETS].update_one(
                    {"_id": ObjectId(ticket_id)},
                    {
                        "$set": {
                            "estado": status,
                            "notas": notes,
                            "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
                return result.modified_count > 0
            except Exception as e:
                logger.error(f"MongoDB update_ticket error: {e}")
        return False

    def insert_notification(self, notification: Dict) -> Optional[str]:
        """Registra una notificación enviada."""
        notification = notification.copy()
        notification.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        if self.is_connected():
            try:
                result = self._db[COL_NOTIFICATIONS].insert_one(notification)
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"MongoDB insert_notification error: {e}")

        return self._json_append(COL_NOTIFICATIONS, notification)

    def save_system_status(self, status: Dict) -> Optional[str]:
        """Guarda un snapshot del estado del sistema."""
        status = status.copy()
        status.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        if self.is_connected():
            try:
                result = self._db[COL_SYSTEM_STATUS].insert_one(status)
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"MongoDB save_system_status error: {e}")

        return self._json_append(COL_SYSTEM_STATUS, status)

    def save_srgan_result(self, result: Dict) -> Optional[str]:
        """Guarda metadatos de un resultado de super-resolución."""
        result = result.copy()
        result.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        if self.is_connected():
            try:
                res = self._db[COL_SRGAN_RESULTS].insert_one(result)
                return str(res.inserted_id)
            except Exception as e:
                logger.error(f"MongoDB save_srgan_result error: {e}")

        return self._json_append(COL_SRGAN_RESULTS, result)

    # ─── Estadísticas ─────────────────────────────────────────────────────────
    def get_statistics(self, days_back: int = 30) -> Dict:
        """
        Calcula estadísticas del sistema para el período especificado.

        Returns:
            Diccionario con métricas agregadas.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

        if self.is_connected():
            try:
                pipeline = [
                    {"$match": {"timestamp": {"$gte": cutoff}}},
                    {
                        "$group": {
                            "_id": None,
                            "total_detections": {"$sum": 1},
                            "avg_score": {"$avg": "$elite_score"},
                            "max_score": {"$max": "$elite_score"},
                            "total_loss_usd": {"$sum": "$perdida_usd_dia"},
                            "total_co2e": {"$sum": "$co2e_ton_year"},
                            "avg_ch4_ppb": {"$avg": "$ch4_ppb_total"},
                        }
                    },
                ]
                results = list(self._db[COL_DETECTIONS].aggregate(pipeline))
                if results:
                    stats = results[0]
                    stats.pop("_id", None)
                    stats["period_days"] = days_back
                    stats["elite_alerts"] = self._db[COL_DETECTIONS].count_documents(
                        {"timestamp": {"$gte": cutoff}, "elite_score": {"$gte": 80}}
                    )
                    stats["total_tickets"] = self._db[COL_TICKETS].count_documents(
                        {"fecha_creacion": {"$gte": cutoff}}
                    )
                    return stats
            except Exception as e:
                logger.error(f"MongoDB get_statistics error: {e}")

        # Fallback: calcular desde JSON
        return self._json_statistics(days_back)

    def get_persistence_by_asset(self, days_back: int = 30) -> List[Dict]:
        """
        Calcula la persistencia de fugas por activo (cuántos días con anomalía).

        Returns:
            Lista de activos con su conteo de días con detección.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

        if self.is_connected():
            try:
                pipeline = [
                    {"$match": {"timestamp": {"$gte": cutoff}}},
                    {
                        "$group": {
                            "_id": "$nombre",
                            "detection_count": {"$sum": 1},
                            "avg_score": {"$avg": "$elite_score"},
                            "max_score": {"$max": "$elite_score"},
                            "avg_anomaly": {"$avg": "$ch4_ppb_anomaly"},
                            "total_loss_usd": {"$sum": "$perdida_usd_dia"},
                            "operador": {"$first": "$operador"},
                            "tipo": {"$first": "$tipo"},
                        }
                    },
                    {"$sort": {"max_score": -1}},
                ]
                results = list(self._db[COL_DETECTIONS].aggregate(pipeline))
                for r in results:
                    r["nombre"] = r.pop("_id")
                    r["persistence_days"] = r["detection_count"]
                return results
            except Exception as e:
                logger.error(f"MongoDB get_persistence_by_asset error: {e}")

        return []

    # ─── Migración desde JSON ─────────────────────────────────────────────────
    def migrate_from_json(self, json_path: str) -> int:
        """
        Migra datos históricos desde event_master_table.json a MongoDB.

        Args:
            json_path: Ruta al archivo JSON con historial de eventos.

        Returns:
            Número de documentos migrados.
        """
        if not os.path.exists(json_path):
            logger.warning(f"Archivo JSON no encontrado: {json_path}")
            return 0

        try:
            with open(json_path) as f:
                events = json.load(f)

            if not isinstance(events, list):
                events = [events]

            if not events:
                return 0

            if self.is_connected():
                # Evitar duplicados usando upsert
                count = 0
                for event in events:
                    event.setdefault("migrated_from_json", True)
                    event.setdefault("migration_date", datetime.now(timezone.utc).isoformat())
                    try:
                        self._db[COL_EVENTS].update_one(
                            {
                                "nombre": event.get("nombre"),
                                "timestamp": event.get("timestamp"),
                            },
                            {"$setOnInsert": event},
                            upsert=True,
                        )
                        count += 1
                    except Exception:
                        pass

                logger.info(f"MongoDB: migrados {count} eventos desde {json_path}")
                return count
            else:
                logger.warning("MongoDB no conectado. No se puede migrar.")
                return 0
        except Exception as e:
            logger.error(f"Error migrando desde JSON: {e}")
            return 0

    # ─── Fallback JSON ────────────────────────────────────────────────────────
    def _json_path(self, collection: str) -> str:
        return os.path.join(self.data_dir, f"{collection}.json")

    def _json_append(self, collection: str, document: Dict) -> str:
        """Agrega un documento al archivo JSON de la colección."""
        path = self._json_path(collection)
        data = []
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                data = []

        if not isinstance(data, list):
            data = []

        doc_id = f"json_{len(data)}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        document["_json_id"] = doc_id
        data.append(document)

        with open(path, "w") as f:
            json.dump(data[-10000:], f, indent=2, ensure_ascii=False)  # Máx 10k registros

        return doc_id

    def _json_query(
        self,
        collection: str,
        nombre: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
    ) -> List[Dict]:
        """Consulta básica sobre archivo JSON."""
        path = self._json_path(collection)
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []

            cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            results = [
                d for d in data
                if d.get("timestamp", "") >= cutoff
                and (not nombre or d.get("nombre") == nombre)
            ]
            return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        except Exception as e:
            logger.error(f"JSON query error ({collection}): {e}")
            return []

    def _json_statistics(self, days_back: int) -> Dict:
        """Calcula estadísticas básicas desde JSON."""
        detections = self._json_query(COL_DETECTIONS, days_back=days_back, limit=10000)
        if not detections:
            return {"period_days": days_back, "total_detections": 0}

        scores = [d.get("elite_score", 0) for d in detections]
        losses = [d.get("perdida_usd_dia", 0) for d in detections]
        co2e = [d.get("co2e_ton_year", 0) for d in detections]
        ch4 = [d.get("ch4_ppb_total", 0) for d in detections]

        import statistics as st
        return {
            "period_days": days_back,
            "total_detections": len(detections),
            "avg_score": round(st.mean(scores), 2) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "total_loss_usd": round(sum(losses), 2),
            "total_co2e": round(sum(co2e), 2),
            "avg_ch4_ppb": round(st.mean(ch4), 1) if ch4 else 0,
            "elite_alerts": sum(1 for s in scores if s >= 80),
        }

    # ─── Estado del módulo ────────────────────────────────────────────────────
    def get_status(self) -> Dict:
        """Retorna el estado de la conexión y estadísticas básicas."""
        status = {
            "pymongo_available": self._pymongo_available,
            "connected": self.is_connected(),
            "uri": self.uri.replace(
                self.uri.split("@")[0] if "@" in self.uri else "", "***"
            ),
            "database": self.db_name,
            "mode": "mongodb" if self.is_connected() else "json_fallback",
        }

        if self.is_connected():
            try:
                status["collections"] = {
                    col: self._db[col].count_documents({})
                    for col in [
                        COL_DETECTIONS, COL_EVENTS, COL_TICKETS,
                        COL_NOTIFICATIONS, COL_SYSTEM_STATUS,
                    ]
                }
            except Exception:
                pass

        return status

    def close(self):
        """Cierra la conexión MongoDB."""
        if self._client:
            try:
                self._client.close()
                self._connected = False
                logger.info("MongoDB: conexión cerrada.")
            except Exception:
                pass
