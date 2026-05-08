"""
auto_pipeline_v55.py — Scheduler Automático + Sistema de Tickets Auto-Generados
=================================================================================
Resuelve dos problemas de producción:

  1. PIPELINE NO SE EJECUTABA AUTOMÁTICAMENTE:
     APScheduler corre el pipeline cada 3 horas alineado con las pasadas
     descendentes de Sentinel-5P sobre Latinoamérica (~13:30 UTC, ~16:30 UTC, etc.)

  2. CRÍTICOS NO GENERABAN TICKETS:
     Después de cada pipeline, las detecciones con score >= UMBRAL_TICKET (60)
     se convierten automáticamente en tickets de intervención persistidos en
     Supabase (tabla tickets) + JSON local + notificación Telegram.

Constantes de producción:
  - PIPELINE_INTERVAL_HOURS = 3      (4 ciclos por día UTC)
  - UMBRAL_TICKET_AUTO     = 60      (CRÍTICO + ÉLITE)
  - UMBRAL_TICKET_ELITE    = 80      (escalación inmediata)
"""
import logging
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

# ─── Constantes ─────────────────────────────────────────────────────────────
PIPELINE_INTERVAL_HOURS = int(os.getenv("PIPELINE_INTERVAL_HOURS", "3"))
UMBRAL_TICKET_AUTO      = float(os.getenv("UMBRAL_TICKET_AUTO", "60"))
UMBRAL_TICKET_ELITE     = float(os.getenv("UMBRAL_TICKET_ELITE", "80"))
SLA_HORAS_ELITE         = int(os.getenv("SLA_HORAS_ELITE", "4"))
SLA_HORAS_CRITICO       = int(os.getenv("SLA_HORAS_CRITICO", "24"))
SLA_HORAS_VIGILANCIA    = int(os.getenv("SLA_HORAS_VIGILANCIA", "72"))


# ─── Generador automático de tickets ────────────────────────────────────────
class AutoTicketGenerator:
    """
    Convierte detecciones de alto score en tickets de intervención.
    Persiste en Supabase + JSON local. Evita duplicados por (activo, fecha).
    """

    def __init__(self, tickets_dir: str, supabase_db=None, telegram_notifier=None,
                 broadcast_fn: Optional[Callable] = None):
        self.tickets_dir = Path(tickets_dir)
        self.tickets_dir.mkdir(parents=True, exist_ok=True)
        self.supabase = supabase_db
        self.telegram = telegram_notifier
        self.broadcast = broadcast_fn  # async fn(event_type, data) for WebSocket

    def _load_recent_tickets(self) -> Dict[str, Dict]:
        """Carga tickets recientes para detectar duplicados (clave: activo+fecha)."""
        recent = {}
        try:
            for f in sorted(self.tickets_dir.glob("ticket_*.json"), reverse=True)[:200]:
                try:
                    t = json.loads(f.read_text())
                    key = f"{t.get('activo','')}_{(t.get('fecha_deteccion','') or '')[:10]}"
                    recent[key] = t
                except Exception:
                    continue
        except Exception:
            pass
        return recent

    def _classify(self, score: float) -> Dict:
        """Clasifica un score en categoría, prioridad, SLA."""
        if score >= UMBRAL_TICKET_ELITE:
            return {
                "categoria": "ELITE",
                "prioridad": "P0",
                "color": "#ff2244",
                "sla_horas": SLA_HORAS_ELITE,
                "accion": "INSPECCION_INMEDIATA",
                "escalacion": "DIRECTOR_OPERACIONES",
            }
        elif score >= UMBRAL_TICKET_AUTO:
            return {
                "categoria": "CRITICO",
                "prioridad": "P1",
                "color": "#ff8c00",
                "sla_horas": SLA_HORAS_CRITICO,
                "accion": "VERIFICAR_EN_CAMPO",
                "escalacion": "JEFE_HSE",
            }
        else:
            return {
                "categoria": "VIGILANCIA",
                "prioridad": "P2",
                "color": "#ffd700",
                "sla_horas": SLA_HORAS_VIGILANCIA,
                "accion": "MONITOREAR",
                "escalacion": "OPERADOR",
            }

    def generate_for_detection(self, det: Dict) -> Optional[Dict]:
        """Genera un ticket para una detección si supera el umbral."""
        score = det.get("score_prioridad") or det.get("elite_score") or 0
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        if score < UMBRAL_TICKET_AUTO:
            return None

        activo = det.get("activo_cercano", "desconocido")
        fecha_det = det.get("fecha_deteccion", datetime.now(timezone.utc).isoformat())
        clasif = self._classify(score)

        creado_en = datetime.now(timezone.utc)
        ticket_id = f"TKT-{creado_en.strftime('%Y%m%d-%H%M%S')}-{activo[:8].upper().replace(' ', '')}"
        sla_deadline = creado_en + timedelta(hours=clasif["sla_horas"])

        ticket = {
            "ticket_id":         ticket_id,
            "estado":            "ABIERTO",
            "fuente":            "AUTO_PIPELINE_V55",
            "categoria":         clasif["categoria"],
            "prioridad":         clasif["prioridad"],
            "color":             clasif["color"],
            "accion_recomendada": clasif["accion"],
            "escalar_a":         clasif["escalacion"],
            "creado_en":         creado_en.isoformat(),
            "sla_deadline":      sla_deadline.isoformat(),
            "sla_horas":         clasif["sla_horas"],

            # Información de la detección
            "activo":            activo,
            "operador":          det.get("operador", ""),
            "tipo_activo":       det.get("tipo_activo", ""),
            "latitud":           det.get("latitud"),
            "longitud":          det.get("longitud"),
            "fecha_deteccion":   fecha_det,
            "ch4_ppb":           det.get("intensidad_ppb", det.get("ch4_ppb_total", 0)),
            "ch4_anomaly_ppb":   det.get("ch4_ppb_anomaly", 0),
            "score":             round(score, 2),
            "perdida_usd_dia":   det.get("perdida_economica_usd_dia", 0),
            "viento_velocidad":  det.get("viento_dominante_velocidad", 0),
            "viento_direccion":  det.get("viento_dominante_direccion", 0),

            # Estado y tracking
            "asignado_a":        None,
            "notas":             [],
            "historial":         [{
                "ts":       creado_en.isoformat(),
                "evento":   "TICKET_CREADO_AUTOMATICAMENTE",
                "actor":    "system",
                "detalle":  f"Auto-generado por pipeline. Score={score:.1f} ({clasif['categoria']})",
            }],
            "fuente_datos":      "Copernicus Sentinel-5P TROPOMI + Open-Meteo CAMS",
        }

        # Persistir en disco
        try:
            (self.tickets_dir / f"ticket_{ticket_id}.json").write_text(
                json.dumps(ticket, indent=2, ensure_ascii=False, default=str)
            )
        except Exception as e:
            logger.error(f"Error guardando ticket {ticket_id} en disco: {e}")

        # Persistir en Supabase
        if self.supabase:
            try:
                self.supabase.insert_ticket(ticket)
            except Exception as e:
                logger.warning(f"Error insertando ticket en Supabase: {e}")

        return ticket

    def process_batch(self, detections: List[Dict]) -> Dict:
        """Procesa un lote de detecciones y genera tickets para los críticos."""
        recent = self._load_recent_tickets()
        creados = []
        skipped_dup = 0
        for det in detections:
            score = det.get("score_prioridad") or det.get("elite_score") or 0
            try:
                score = float(score)
            except (TypeError, ValueError):
                continue
            if score < UMBRAL_TICKET_AUTO:
                continue
            activo = det.get("activo_cercano", "")
            fecha_d = (det.get("fecha_deteccion", "") or "")[:10]
            key = f"{activo}_{fecha_d}"
            if key in recent:
                skipped_dup += 1
                continue
            t = self.generate_for_detection(det)
            if t:
                creados.append(t)
                recent[key] = t

        return {
            "tickets_creados": len(creados),
            "duplicados_omitidos": skipped_dup,
            "elite_p0": sum(1 for t in creados if t["categoria"] == "ELITE"),
            "critico_p1": sum(1 for t in creados if t["categoria"] == "CRITICO"),
            "tickets": creados,
        }


# ─── Scheduler ──────────────────────────────────────────────────────────────
class PipelineScheduler:
    """
    Wrapper sobre APScheduler para correr el pipeline real cada N horas
    + ticket post-procesamiento automático.
    """

    def __init__(self, run_pipeline_fn: Callable, ticket_generator: AutoTicketGenerator,
                 broadcast_fn: Optional[Callable] = None):
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError as e:
            raise RuntimeError(f"APScheduler no disponible: {e}")

        self._AsyncIOScheduler = AsyncIOScheduler
        self._CronTrigger = CronTrigger
        self._IntervalTrigger = IntervalTrigger
        self.run_pipeline_fn = run_pipeline_fn
        self.ticket_gen = ticket_generator
        self.broadcast = broadcast_fn
        self.scheduler = None
        self.last_run = None
        self.next_run = None
        self.runs_count = 0
        self.errors_count = 0

    async def _job(self):
        """Job que corre el pipeline real."""
        self.runs_count += 1
        self.last_run = datetime.now(timezone.utc)
        logger.info(f"[Scheduler] Ejecutando pipeline automático #{self.runs_count}")
        try:
            if self.broadcast:
                await self.broadcast("scheduler.tick", {
                    "run_number": self.runs_count,
                    "started_at": self.last_run.isoformat(),
                })
            # Pipeline real para AYER (Sentinel-5P publica con ~24h de delay)
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            await self.run_pipeline_fn(yesterday)
        except Exception as e:
            self.errors_count += 1
            logger.error(f"[Scheduler] Error en pipeline automático: {e}", exc_info=True)
            if self.broadcast:
                try:
                    await self.broadcast("scheduler.error", {"error": str(e)[:300]})
                except Exception:
                    pass

    def start(self):
        """Inicia el scheduler."""
        if self.scheduler:
            return
        self.scheduler = self._AsyncIOScheduler(timezone="UTC")
        # 4 ejecuciones diarias alineadas con pasadas de Sentinel-5P sobre LatAm:
        # 14:00, 17:00, 20:00, 23:00 UTC (≈ 09:00, 12:00, 15:00, 18:00 hora Colombia)
        cron = self._CronTrigger(hour="14,17,20,23", minute=15)
        self.scheduler.add_job(
            self._job,
            cron,
            id="pipeline_auto",
            name="Pipeline Sentinel-5P Auto",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
        self.scheduler.start()
        # Calcular próxima ejecución
        try:
            self.next_run = self.scheduler.get_job("pipeline_auto").next_run_time
        except Exception:
            self.next_run = None
        logger.info(
            f"[Scheduler] APScheduler iniciado: 4 ejecuciones diarias "
            f"(14:15, 17:15, 20:15, 23:15 UTC). Próxima: {self.next_run}"
        )

    def stop(self):
        if self.scheduler:
            try:
                self.scheduler.shutdown(wait=False)
            except Exception:
                pass
            self.scheduler = None

    def status(self) -> Dict:
        next_run = None
        if self.scheduler:
            try:
                next_run = self.scheduler.get_job("pipeline_auto").next_run_time
                if next_run:
                    next_run = next_run.isoformat()
            except Exception:
                pass
        return {
            "running":          self.scheduler is not None,
            "runs_total":       self.runs_count,
            "errors_total":     self.errors_count,
            "last_run":         self.last_run.isoformat() if self.last_run else None,
            "next_run":         next_run,
            "schedule":         "Cron: 14:15, 17:15, 20:15, 23:15 UTC (4×día)",
            "alineacion":       "Pasadas descendentes Sentinel-5P sobre Latinoamérica",
            "umbral_ticket":    UMBRAL_TICKET_AUTO,
            "umbral_elite":     UMBRAL_TICKET_ELITE,
        }
