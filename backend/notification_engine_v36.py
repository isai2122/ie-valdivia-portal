"""
notification_engine_v36.py — MetanoSRGAN Elite v3.6
Sistema de notificaciones automáticas Slack y Email.

Dispara alertas cuando Elite Score ≥ 80 (umbral configurable).
Soporta:
  - Slack: Webhook con bloques visuales enriquecidos (Block Kit)
  - Email: SMTP con HTML formateado (Gmail, Outlook, SMTP genérico)
  - Log local: Registro de todas las notificaciones enviadas

Configuración vía variables de entorno (.env):
  SLACK_WEBHOOK_URL   — URL del webhook de Slack
  EMAIL_SMTP_HOST     — Servidor SMTP (ej: smtp.gmail.com)
  EMAIL_SMTP_PORT     — Puerto SMTP (587 para TLS, 465 para SSL)
  EMAIL_FROM          — Dirección de origen
  EMAIL_PASSWORD      — Contraseña o App Password
  EMAIL_TO            — Destinatario(s), separados por coma
  ELITE_SCORE_THRESHOLD — Umbral de alerta (default: 80)
"""

import os
import json
import logging
import smtplib
import ssl
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
ELITE_SCORE_THRESHOLD = int(os.getenv("ELITE_SCORE_THRESHOLD", "80"))
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
NOTIFICATION_LOG_PATH = os.getenv(
    "NOTIFICATION_LOG_PATH",
    "/home/ubuntu/metanosrgan_v36/data/notification_log.json",
)

# Colores por nivel de alerta
ALERT_COLORS = {
    "CRITICA":  {"hex": "#FF0000", "emoji": "🚨", "slack_color": "danger"},
    "ALTA":     {"hex": "#FF8C00", "emoji": "⚠️",  "slack_color": "warning"},
    "MEDIA":    {"hex": "#FFD700", "emoji": "📊", "slack_color": "#FFD700"},
    "BAJA":     {"hex": "#00AA00", "emoji": "✅", "slack_color": "good"},
}


def _get_alert_level(elite_score: float) -> str:
    if elite_score >= 100:
        return "CRITICA"
    elif elite_score >= 80:
        return "ALTA"
    elif elite_score >= 60:
        return "MEDIA"
    return "BAJA"


class NotificationEngine:
    """
    Motor de notificaciones automáticas para MetanoSRGAN Elite.
    Envía alertas Slack y/o Email cuando Elite Score supera el umbral.
    """

    def __init__(
        self,
        slack_webhook: str = SLACK_WEBHOOK_URL,
        email_from: str = EMAIL_FROM,
        email_password: str = EMAIL_PASSWORD,
        email_to: str = EMAIL_TO,
        smtp_host: str = EMAIL_SMTP_HOST,
        smtp_port: int = EMAIL_SMTP_PORT,
        threshold: int = ELITE_SCORE_THRESHOLD,
        log_path: str = NOTIFICATION_LOG_PATH,
    ):
        self.slack_webhook = slack_webhook
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = [e.strip() for e in email_to.split(",") if e.strip()]
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.threshold = threshold
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._notification_log: List[Dict] = self._load_log()

    # ─── Log de notificaciones ────────────────────────────────────────────────
    def _load_log(self) -> List[Dict]:
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_log(self):
        with open(self.log_path, "w") as f:
            json.dump(self._notification_log[-500:], f, indent=2, ensure_ascii=False)

    def _log_notification(self, detection: Dict, channels: List[str], success: bool):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nombre": detection.get("nombre"),
            "elite_score": detection.get("elite_score"),
            "ch4_ppb": detection.get("ch4_ppb_total"),
            "anomaly_ppb": detection.get("ch4_ppb_anomaly"),
            "alert_level": _get_alert_level(detection.get("elite_score", 0)),
            "channels": channels,
            "success": success,
        }
        self._notification_log.append(entry)
        self._save_log()

    # ─── Slack ────────────────────────────────────────────────────────────────
    def send_slack_alert(self, detection: Dict) -> bool:
        """
        Envía alerta de metano a Slack usando Block Kit.
        Incluye mapa de ubicación, métricas y enlace al dashboard.
        """
        if not self.slack_webhook:
            logger.debug("Slack webhook no configurado.")
            return False

        score = detection.get("elite_score", 0)
        nombre = detection.get("nombre", "Desconocido")
        ppb = detection.get("ch4_ppb_total", 0)
        anomaly = detection.get("ch4_ppb_anomaly", 0)
        flujo = detection.get("flujo_kg_h", 0)
        perdida = detection.get("perdida_usd_dia", 0)
        co2e = detection.get("co2e_ton_year", 0)
        operador = detection.get("operador", "N/A")
        tipo = detection.get("tipo", "N/A")
        lat = detection.get("lat", 0)
        lon = detection.get("lon", 0)
        level = _get_alert_level(score)
        color_info = ALERT_COLORS[level]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Construir mensaje Block Kit
        payload = {
            "attachments": [
                {
                    "color": color_info["slack_color"],
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{color_info['emoji']} ALERTA METANO {level} — {nombre}",
                                "emoji": True,
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Elite Score:*\n`{score:.1f} / 120`"},
                                {"type": "mrkdwn", "text": f"*Nivel:*\n`{level}`"},
                                {"type": "mrkdwn", "text": f"*CH4 Total:*\n`{ppb:.1f} ppb`"},
                                {"type": "mrkdwn", "text": f"*Anomalía:*\n`+{anomaly:.1f} ppb`"},
                                {"type": "mrkdwn", "text": f"*Flujo:*\n`{flujo:.2f} kg/h`"},
                                {"type": "mrkdwn", "text": f"*Pérdida:*\n`${perdida:.2f} USD/día`"},
                                {"type": "mrkdwn", "text": f"*CO₂e:*\n`{co2e:.1f} Ton/año`"},
                                {"type": "mrkdwn", "text": f"*Operador:*\n`{operador}`"},
                                {"type": "mrkdwn", "text": f"*Tipo:*\n`{tipo}`"},
                                {"type": "mrkdwn", "text": f"*Coordenadas:*\n`{lat:.3f}°N, {lon:.3f}°W`"},
                            ],
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Timestamp:* {timestamp}\n"
                                    f"*Sistema:* MetanoSRGAN Elite v3.6\n"
                                    f"*Zona:* Magdalena Medio, Colombia"
                                ),
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Ver Dashboard"},
                                    "url": "http://localhost:8000",
                                    "style": "primary",
                                },
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Ver en Mapa"},
                                    "url": (
                                        f"https://www.google.com/maps?q={lat},{lon}"
                                    ),
                                },
                            ],
                        },
                    ],
                }
            ]
        }

        try:
            resp = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"Slack: alerta enviada para {nombre} (score={score:.1f})")
                return True
            else:
                logger.error(f"Slack error: {resp.status_code} — {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Slack: error enviando alerta: {e}")
            return False

    # ─── Email ────────────────────────────────────────────────────────────────
    def send_email_alert(self, detection: Dict) -> bool:
        """
        Envía alerta de metano por email con HTML formateado.
        Compatible con Gmail (App Password), Outlook y SMTP genérico.
        """
        if not self.email_from or not self.email_password or not self.email_to:
            logger.debug("Email no configurado.")
            return False

        score = detection.get("elite_score", 0)
        nombre = detection.get("nombre", "Desconocido")
        ppb = detection.get("ch4_ppb_total", 0)
        anomaly = detection.get("ch4_ppb_anomaly", 0)
        flujo = detection.get("flujo_kg_h", 0)
        perdida = detection.get("perdida_usd_dia", 0)
        co2e = detection.get("co2e_ton_year", 0)
        operador = detection.get("operador", "N/A")
        tipo = detection.get("tipo", "N/A")
        lat = detection.get("lat", 0)
        lon = detection.get("lon", 0)
        level = _get_alert_level(score)
        color_info = ALERT_COLORS[level]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        subject = (
            f"[MetanoSRGAN] {color_info['emoji']} ALERTA {level} — "
            f"{nombre} | Elite Score: {score:.1f}"
        )

        html_body = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px;
                  box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
    .header {{ background: {color_info['hex']}; color: white; padding: 20px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .header p {{ margin: 5px 0 0; opacity: 0.9; }}
    .body {{ padding: 25px; }}
    .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
    .metric {{ background: #f8f9fa; border-radius: 6px; padding: 12px; text-align: center; }}
    .metric .value {{ font-size: 22px; font-weight: bold; color: {color_info['hex']}; }}
    .metric .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    .info-table td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
    .info-table td:first-child {{ font-weight: bold; color: #333; width: 40%; }}
    .footer {{ background: #333; color: #aaa; padding: 15px; text-align: center; font-size: 12px; }}
    .btn {{ display: inline-block; background: {color_info['hex']}; color: white;
             padding: 10px 20px; border-radius: 5px; text-decoration: none;
             margin: 5px; font-weight: bold; }}
    .alert-badge {{ display: inline-block; background: {color_info['hex']}; color: white;
                    padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{color_info['emoji']} ALERTA DE METANO</h1>
      <p>MetanoSRGAN Elite v3.6 — Magdalena Medio, Colombia</p>
    </div>
    <div class="body">
      <p>Se ha detectado una fuga de metano con nivel <span class="alert-badge">{level}</span>
         en el activo <strong>{nombre}</strong> ({operador}).</p>

      <div class="metric-grid">
        <div class="metric">
          <div class="value">{score:.1f}</div>
          <div class="label">Elite Score (máx 120)</div>
        </div>
        <div class="metric">
          <div class="value">{ppb:.0f} ppb</div>
          <div class="label">CH4 Total</div>
        </div>
        <div class="metric">
          <div class="value">+{anomaly:.0f} ppb</div>
          <div class="label">Anomalía sobre fondo</div>
        </div>
        <div class="metric">
          <div class="value">{flujo:.2f} kg/h</div>
          <div class="label">Flujo de emisión</div>
        </div>
        <div class="metric">
          <div class="value">${perdida:.2f}</div>
          <div class="label">Pérdida USD/día</div>
        </div>
        <div class="metric">
          <div class="value">{co2e:.1f} Ton</div>
          <div class="label">CO₂e / año</div>
        </div>
      </div>

      <table class="info-table">
        <tr><td>Activo</td><td>{nombre}</td></tr>
        <tr><td>Operador</td><td>{operador}</td></tr>
        <tr><td>Tipo</td><td>{tipo}</td></tr>
        <tr><td>Coordenadas</td><td>{lat:.4f}°N, {lon:.4f}°W</td></tr>
        <tr><td>Timestamp</td><td>{timestamp}</td></tr>
        <tr><td>Fuente datos</td><td>Sentinel-5P / Open-Meteo CAMS</td></tr>
        <tr><td>Resolución</td><td>10 metros (Super-Resolución SRGAN)</td></tr>
      </table>

      <p style="text-align:center; margin-top: 20px;">
        <a href="http://localhost:8000" class="btn">Ver Dashboard</a>
        <a href="https://www.google.com/maps?q={lat},{lon}" class="btn">Ver en Mapa</a>
      </p>
    </div>
    <div class="footer">
      <p>MetanoSRGAN Elite v3.6 — Sistema de Inteligencia Predictiva 24/7</p>
      <p>Zona: Magdalena Medio, Colombia | Activos: Ecopetrol / TGI</p>
      <p>Este es un mensaje automático. No responder a este correo.</p>
    </div>
  </div>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(self.email_from, self.email_password)
                server.sendmail(self.email_from, self.email_to, msg.as_string())
            logger.info(
                f"Email: alerta enviada a {self.email_to} "
                f"para {nombre} (score={score:.1f})"
            )
            return True
        except Exception as e:
            logger.error(f"Email: error enviando alerta: {e}")
            return False

    # ─── Método principal ─────────────────────────────────────────────────────
    def process_detections(self, detections: List[Dict]) -> Dict:
        """
        Procesa una lista de detecciones y envía notificaciones
        para aquellas que superen el umbral de Elite Score.

        Args:
            detections: Lista de detecciones del pipeline principal.

        Returns:
            Resumen de notificaciones enviadas.
        """
        alerts_sent = 0
        alerts_failed = 0
        notified = []

        for det in detections:
            score = det.get("elite_score", 0)
            if score < self.threshold:
                continue

            nombre = det.get("nombre", "?")
            level = _get_alert_level(score)
            channels_ok = []
            channels_fail = []

            logger.info(
                f"Notificación: {nombre} — Elite Score {score:.1f} ≥ {self.threshold} "
                f"(nivel: {level})"
            )

            # Enviar Slack
            if self.slack_webhook:
                if self.send_slack_alert(det):
                    channels_ok.append("slack")
                else:
                    channels_fail.append("slack")

            # Enviar Email
            if self.email_from and self.email_to:
                if self.send_email_alert(det):
                    channels_ok.append("email")
                else:
                    channels_fail.append("email")

            success = len(channels_ok) > 0
            self._log_notification(det, channels_ok + channels_fail, success)

            if success:
                alerts_sent += 1
                notified.append({
                    "nombre": nombre,
                    "score": score,
                    "level": level,
                    "channels": channels_ok,
                })
            else:
                alerts_failed += 1

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threshold": self.threshold,
            "detections_evaluated": len(detections),
            "alerts_triggered": alerts_sent + alerts_failed,
            "alerts_sent_ok": alerts_sent,
            "alerts_failed": alerts_failed,
            "notified": notified,
            "slack_configured": bool(self.slack_webhook),
            "email_configured": bool(self.email_from and self.email_to),
        }

        if alerts_sent > 0:
            logger.info(
                f"Notificaciones: {alerts_sent} enviadas, {alerts_failed} fallidas "
                f"de {len(detections)} detecciones evaluadas."
            )

        return summary

    # ─── Prueba de conectividad ───────────────────────────────────────────────
    def test_slack(self) -> bool:
        """Envía un mensaje de prueba a Slack."""
        if not self.slack_webhook:
            logger.warning("Slack webhook no configurado.")
            return False
        try:
            resp = requests.post(
                self.slack_webhook,
                json={"text": "✅ MetanoSRGAN Elite v3.6 — Test de conectividad Slack OK"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Slack test error: {e}")
            return False

    def test_email(self) -> bool:
        """Envía un email de prueba."""
        if not self.email_from or not self.email_to:
            logger.warning("Email no configurado.")
            return False
        test_det = {
            "nombre": "TEST — Barrancabermeja",
            "elite_score": 85.0,
            "ch4_ppb_total": 2100.0,
            "ch4_ppb_anomaly": 180.0,
            "flujo_kg_h": 12.5,
            "perdida_usd_dia": 60.0,
            "co2e_ton_year": 3066.0,
            "operador": "Ecopetrol",
            "tipo": "Refinería",
            "lat": 7.065,
            "lon": -73.850,
        }
        return self.send_email_alert(test_det)

    def get_notification_history(self, last_n: int = 50) -> List[Dict]:
        """Retorna el historial de notificaciones enviadas."""
        return self._notification_log[-last_n:]

    def get_status(self) -> Dict:
        """Retorna el estado de configuración del motor de notificaciones."""
        return {
            "threshold": self.threshold,
            "slack_configured": bool(self.slack_webhook),
            "email_configured": bool(self.email_from and self.email_to),
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "email_from": self.email_from,
            "email_to": self.email_to,
            "total_notifications_sent": len(self._notification_log),
            "last_notification": (
                self._notification_log[-1]["timestamp"]
                if self._notification_log else None
            ),
        }
