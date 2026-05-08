"""
telegram_notifier_v39.py — MetanoSRGAN Elite v3.9
Módulo de integración: Pipeline → Bot de Telegram @MetanoAlerts_bot

Permite al pipeline principal enviar alertas directamente al bot de Telegram.
Se integra con notification_engine_v36.py como canal adicional.
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ─── Configuración ────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8697859059:AAGIvGErN1E764bvQ1sYcc5vHZNFYKAsOkY")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Archivo de suscriptores (compartido con el bot)
_BOT_DIR = os.path.join(os.path.dirname(__file__), "..", "telegram_bot")
SUBSCRIBERS_FILE = os.path.join(_BOT_DIR, "subscribers.json")

# Umbral Elite Score para notificaciones
ELITE_SCORE_THRESHOLD = float(os.getenv("ELITE_SCORE_THRESHOLD", "50"))


def _load_subscribers() -> List[int]:
    """Carga la lista de chat_ids suscritos."""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
    """Envía un mensaje a un chat de Telegram."""
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            logger.warning(f"Telegram API error {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Error enviando mensaje Telegram a {chat_id}: {e}")
        return False


def _elite_score_emoji(score: float) -> str:
    if score >= 80:
        return "🔴"
    elif score >= 60:
        return "🟠"
    elif score >= 40:
        return "🟡"
    else:
        return "🟢"


class TelegramNotifier:
    """
    Notificador de Telegram para MetanoSRGAN Elite v3.9.
    Se integra con el pipeline principal para enviar alertas automáticas.
    """

    def __init__(self, threshold: float = ELITE_SCORE_THRESHOLD):
        self.threshold = threshold
        self._sent_cache: set = set()  # Para evitar duplicados
        logger.info(
            f"TelegramNotifier inicializado (threshold={threshold}, "
            f"bot=@MetanoAlerts_bot)"
        )

    def is_configured(self) -> bool:
        """Verifica si el bot está configurado y accesible."""
        try:
            resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_subscribers(self) -> List[int]:
        """Obtiene la lista de suscriptores activos."""
        return _load_subscribers()

    def send_alert(self, detection: Dict[str, Any]) -> bool:
        """
        Envía una alerta de detección a todos los suscriptores.

        Args:
            detection: Diccionario con datos de la detección.

        Returns:
            True si se envió a al menos un suscriptor.
        """
        score = float(detection.get("elite_score") or detection.get("score_prioridad") or 0)
        if score < self.threshold:
            return False

        nombre = detection.get("nombre") or detection.get("activo_cercano") or "Activo"
        ch4 = float(detection.get("ch4_ppb_total") or detection.get("intensidad_ppb") or 0)
        anomaly = float(detection.get("ch4_ppb_anomaly") or max(0, ch4 - 1920))
        flujo = float(detection.get("flujo_kg_h") or 0)
        perdida = float(detection.get("perdida_usd_dia") or 0)
        co2e = float(detection.get("co2e_ton_year") or 0)
        operador = detection.get("operador") or "—"
        lat = detection.get("lat") or "—"
        lon = detection.get("lon") or "—"

        # Clave de deduplicación
        cache_key = f"{nombre}_{score:.0f}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        if cache_key in self._sent_cache:
            logger.debug(f"Alerta duplicada ignorada: {cache_key}")
            return False
        self._sent_cache.add(cache_key)

        emoji = _elite_score_emoji(score)
        nivel = "CRÍTICO" if score >= 80 else ("ALTO" if score >= 60 else "MEDIO")

        msg = (
            f"{emoji} *ALERTA METANO — {nombre}*\n\n"
            f"📊 Elite Score: `{score:.1f}` ({nivel})\n"
            f"📡 CH₄: `{ch4:.1f} ppb` (+{anomaly:.1f} ppb)\n"
            f"💨 Flujo: `{flujo:.2f} kg/h`\n"
            f"💰 Pérdida: `${perdida:.2f} USD/día`\n"
            f"🌍 CO₂e: `{co2e:.1f} ton/año`\n"
            f"🏭 Operador: {operador}\n"
        )
        if lat != "—" and lon != "—":
            msg += f"📍 Coords: `{lat}, {lon}`\n"

        msg += (
            f"\n⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"_MetanoSRGAN Elite v3.9 · Magdalena Medio_"
        )

        subs = self.get_subscribers()
        if not subs:
            logger.info("No hay suscriptores de Telegram activos")
            return False

        sent = 0
        for chat_id in subs:
            if _send_message(chat_id, msg):
                sent += 1

        logger.info(f"Alerta Telegram enviada a {sent}/{len(subs)} suscriptores: {nombre} (score={score:.1f})")
        return sent > 0

    def process_detections(self, detections: List[Dict]) -> Dict:
        """
        Procesa una lista de detecciones y envía alertas Telegram.
        Compatible con la interfaz de notification_engine_v36.py.

        Args:
            detections: Lista de detecciones del pipeline.

        Returns:
            Resumen de notificaciones enviadas.
        """
        alerts_sent = 0
        alerts_failed = 0
        notified = []

        subs = self.get_subscribers()

        for det in detections:
            score = float(det.get("elite_score") or det.get("score_prioridad") or 0)
            if score < self.threshold:
                continue

            nombre = det.get("nombre") or det.get("activo_cercano") or "?"
            if self.send_alert(det):
                alerts_sent += 1
                notified.append({
                    "nombre": nombre,
                    "score": score,
                    "channel": "telegram",
                })
            else:
                alerts_failed += 1

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": "telegram",
            "threshold": self.threshold,
            "detections_evaluated": len(detections),
            "alerts_sent_ok": alerts_sent,
            "alerts_failed": alerts_failed,
            "subscribers": len(subs),
            "notified": notified,
            "telegram_configured": self.is_configured(),
        }

    def send_system_status(self, status: Dict) -> bool:
        """Envía el estado del sistema a todos los suscriptores."""
        subs = self.get_subscribers()
        if not subs:
            return False

        version = status.get("version", "3.9")
        sys_status = status.get("system_status", "UNKNOWN")
        last_exec = status.get("last_execution", "—")
        if last_exec and last_exec != "—":
            try:
                last_exec = last_exec[:16].replace("T", " ")
            except Exception:
                pass

        last_results = status.get("last_results", {})
        alertas = last_results.get("total_alertas", 0)
        score_max = last_results.get("elite_score_maximo", 0)

        msg = (
            f"🛰️ *MetanoSRGAN Elite v{version} — Estado*\n\n"
            f"✅ Sistema: `{sys_status}`\n"
            f"⏱️ Última ejecución: `{last_exec}`\n"
            f"📊 Alertas: `{alertas}` | Score máx: `{score_max:.1f}`\n\n"
            f"_Reporte automático · Magdalena Medio_"
        )

        sent = 0
        for chat_id in subs:
            if _send_message(chat_id, msg):
                sent += 1

        return sent > 0

    def send_daily_summary(self, summary: Dict) -> bool:
        """Envía el resumen diario a todos los suscriptores."""
        subs = self.get_subscribers()
        if not subs:
            return False

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        alertas = summary.get("total_alertas", 0)
        criticas = summary.get("alertas_criticas", 0)
        score_max = summary.get("elite_score_maximo", 0)
        perdida = summary.get("perdida_total_usd_dia", 0)
        co2e = summary.get("impacto_co2e_anual_ton", 0)

        msg = (
            f"☀️ *Resumen Diario — {today}*\n\n"
            f"📊 Alertas: `{alertas}` (críticas: `{criticas}`)\n"
            f"🔴 Elite Score máx: `{score_max:.1f}`\n"
            f"💰 Pérdida: `${perdida:.2f} USD/día`\n"
            f"🌍 CO₂e: `{co2e:.1f} ton/año`\n\n"
            f"🛰️ MetanoSRGAN Elite · Magdalena Medio, Colombia\n"
            f"_Usa /detecciones en @MetanoAlerts_bot para detalles_"
        )

        sent = 0
        for chat_id in subs:
            if _send_message(chat_id, msg):
                sent += 1

        logger.info(f"Resumen diario Telegram enviado a {sent}/{len(subs)} suscriptores")
        return sent > 0

    def test_connection(self) -> Dict:
        """Prueba la conexión con el bot."""
        try:
            resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=5)
            if resp.status_code == 200:
                bot_info = resp.json().get("result", {})
                subs = self.get_subscribers()
                return {
                    "status": "ok",
                    "bot_username": bot_info.get("username"),
                    "bot_name": bot_info.get("first_name"),
                    "subscribers": len(subs),
                    "threshold": self.threshold,
                }
            else:
                return {"status": "error", "code": resp.status_code}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Instancia global
telegram_notifier = TelegramNotifier()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("MetanoSRGAN Elite v3.9 — Telegram Notifier Test")
    print("=" * 60)

    result = telegram_notifier.test_connection()
    print(f"\nEstado de conexión:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    if result["status"] == "ok":
        print(f"\n✓ Bot @{result['bot_username']} conectado")
        print(f"✓ Suscriptores activos: {result['subscribers']}")
    else:
        print(f"\n✗ Error de conexión: {result}")
