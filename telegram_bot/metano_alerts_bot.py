"""
metano_alerts_bot.py — MetanoSRGAN Elite v3.9
Bot de Telegram: @MetanoAlerts_bot
Integración completa con MetanoSRGAN Elite v3.8 + Supabase

Funcionalidades:
  - Alertas automáticas de detecciones críticas (Elite Score ≥ 80)
  - Consulta de estado del sistema en tiempo real
  - Últimas detecciones con métricas
  - Resumen diario automático
  - Comandos de administración
  - Integración con Supabase y pipeline local
"""

import os
import sys
import json
import logging
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

# ─── Telegram Bot ─────────────────────────────────────────────────────────────
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)
from telegram.constants import ParseMode

# ─── Configuración ────────────────────────────────────────────────────────────
BOT_TOKEN = "8697859059:AAGIvGErN1E764bvQ1sYcc5vHZNFYKAsOkY"

# Rutas del proyecto
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TICKETS_DIR = BASE_DIR / "tickets"

# Supabase (desde .env)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mfkzozkfggbmcjouiepk.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ma3pvemtmZ2dibWNqb3VpZXBrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyMjgyNTAsImV4cCI6MjA5MjgwNDI1MH0.3VCfNCPVltyJu1eSMs7A8ZcGynWkS-GAEoKcV755Qnc",
)

# API Server local
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# Umbral Elite Score para alertas
ELITE_SCORE_THRESHOLD = float(os.getenv("ELITE_SCORE_THRESHOLD", "50"))

# Archivo de suscriptores (chat_ids autorizados)
SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MetanoAlertsBot")

# ─── Gestión de Suscriptores ──────────────────────────────────────────────────

def load_subscribers() -> List[int]:
    """Carga la lista de chat_ids suscritos."""
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_subscribers(subs: List[int]):
    """Guarda la lista de chat_ids suscritos."""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(set(subs)), f)


def add_subscriber(chat_id: int) -> bool:
    """Añade un suscriptor. Retorna True si era nuevo."""
    subs = load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        save_subscribers(subs)
        return True
    return False


def remove_subscriber(chat_id: int) -> bool:
    """Elimina un suscriptor. Retorna True si existía."""
    subs = load_subscribers()
    if chat_id in subs:
        subs.remove(chat_id)
        save_subscribers(subs)
        return True
    return False


# ─── Fuentes de Datos ─────────────────────────────────────────────────────────

def get_ia_status() -> Dict:
    """Lee el estado del sistema desde el archivo local."""
    status_path = DATA_DIR / "IA_STATUS_24_7.json"
    if status_path.exists():
        try:
            with open(status_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_event_master_table() -> List[Dict]:
    """Lee la tabla maestra de eventos."""
    table_path = DATA_DIR / "event_master_table.json"
    if table_path.exists():
        try:
            with open(table_path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def get_latest_report() -> Dict:
    """Obtiene el reporte operativo más reciente."""
    reports = sorted(DATA_DIR.glob("reporte_operativo_*.json"), reverse=True)
    if reports:
        try:
            with open(reports[0]) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_supabase_detections(limit: int = 10) -> List[Dict]:
    """Obtiene las últimas detecciones desde Supabase."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/detecciones"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        params = {
            "select": "*",
            "order": "fecha_deteccion.desc",
            "limit": limit,
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"Supabase no disponible: {e}")
    return []


def get_api_status() -> Dict:
    """Consulta el estado del API server local."""
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "offline"}


def get_api_detections(limit: int = 10) -> List[Dict]:
    """Obtiene detecciones desde el API server local."""
    try:
        resp = requests.get(f"{API_BASE}/api/detections?limit={limit}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("detections", data if isinstance(data, list) else [])
    except Exception:
        pass
    return []


def get_detections_combined(limit: int = 10) -> List[Dict]:
    """Obtiene detecciones desde Supabase o fallback a API/local."""
    # Intentar Supabase primero
    dets = get_supabase_detections(limit)
    if dets:
        return dets
    # Fallback: API local
    dets = get_api_detections(limit)
    if dets:
        return dets
    # Fallback: tabla maestra local
    events = get_event_master_table()
    return sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]


# ─── Formateo de mensajes ─────────────────────────────────────────────────────

def elite_score_emoji(score: float) -> str:
    if score >= 80:
        return "🔴"
    elif score >= 60:
        return "🟠"
    elif score >= 40:
        return "🟡"
    else:
        return "🟢"


def format_detection(det: Dict, index: int = 1) -> str:
    """Formatea una detección para Telegram."""
    nombre = det.get("nombre") or det.get("activo_cercano") or det.get("activo") or "Desconocido"
    score = float(det.get("elite_score") or det.get("score_prioridad") or 0)
    ch4 = float(det.get("ch4_ppb_total") or det.get("intensidad_ppb") or 0)
    anomaly = float(det.get("ch4_ppb_anomaly") or max(0, ch4 - 1920))
    flujo = float(det.get("flujo_kg_h") or 0)
    perdida = float(det.get("perdida_usd_dia") or 0)
    co2e = float(det.get("co2e_ton_year") or 0)
    operador = det.get("operador") or det.get("empresa") or "—"
    tipo = det.get("tipo") or "—"
    lat = det.get("lat") or det.get("latitude") or "—"
    lon = det.get("lon") or det.get("longitude") or "—"
    ts = det.get("fecha_deteccion") or det.get("timestamp") or "—"
    if ts and ts != "—":
        try:
            ts = ts[:16].replace("T", " ")
        except Exception:
            pass

    emoji = elite_score_emoji(score)
    lines = [
        f"{emoji} *Detección #{index} — {nombre}*",
        f"├ Elite Score: `{score:.1f}`",
        f"├ CH₄ Total: `{ch4:.1f} ppb`",
        f"├ Anomalía: `+{anomaly:.1f} ppb`",
        f"├ Flujo: `{flujo:.2f} kg/h`",
        f"├ Pérdida: `${perdida:.2f} USD/día`",
        f"├ CO₂e: `{co2e:.1f} ton/año`",
        f"├ Operador: {operador}",
        f"├ Tipo: {tipo}",
    ]
    if lat != "—" and lon != "—":
        lines.append(f"├ Coords: `{lat}, {lon}`")
    lines.append(f"└ Fecha: `{ts}`")
    return "\n".join(lines)


# ─── Comandos del Bot ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start — Bienvenida y suscripción."""
    chat_id = update.effective_chat.id
    is_new = add_subscriber(chat_id)

    msg = (
        "🛰️ *MetanoAlerts Bot — MetanoSRGAN Elite v3.9*\n\n"
        "Sistema de monitoreo de metano en el *Magdalena Medio, Colombia*.\n"
        "Detección satelital con IA · Datos Copernicus Sentinel-5P\n\n"
    )
    if is_new:
        msg += "✅ *¡Suscrito exitosamente!* Recibirás alertas automáticas.\n\n"
    else:
        msg += "ℹ️ Ya estás suscrito a las alertas.\n\n"

    msg += (
        "📋 *Comandos disponibles:*\n"
        "/estado — Estado del sistema en tiempo real\n"
        "/detecciones — Últimas detecciones de metano\n"
        "/alerta — Detecciones críticas (Elite Score ≥ 80)\n"
        "/resumen — Resumen ejecutivo del ciclo actual\n"
        "/activos — Lista de activos monitoreados\n"
        "/tickets — Últimos tickets de intervención\n"
        "/mapa — Enlace al dashboard con mapa satelital\n"
        "/suscribir — Activar alertas automáticas\n"
        "/cancelar — Desactivar alertas automáticas\n"
        "/ayuda — Ayuda completa\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
        ],
        [
            InlineKeyboardButton("🚨 Alertas Críticas", callback_data="alerta"),
            InlineKeyboardButton("📋 Resumen", callback_data="resumen"),
        ],
        [
            InlineKeyboardButton("🗺️ Dashboard Web", url="http://localhost:8000"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /estado — Estado del sistema."""
    status = get_ia_status()
    api_status = get_api_status()

    version = status.get("version", "3.8")
    sys_status = status.get("system_status", "UNKNOWN")
    last_exec = status.get("last_execution", "—")
    next_check = status.get("next_check", "—")
    data_source = status.get("data_source", "Copernicus Sentinel-5P")
    last_results = status.get("last_results", {})

    if last_exec and last_exec != "—":
        try:
            last_exec = last_exec[:16].replace("T", " ") + " UTC"
        except Exception:
            pass
    if next_check and next_check != "—":
        try:
            next_check = next_check[:16].replace("T", " ") + " UTC"
        except Exception:
            pass

    api_icon = "🟢" if api_status.get("status") != "offline" else "🔴"
    sys_icon = "🟢" if "OPERATIONAL" in sys_status else "🟡"

    msg = (
        f"🛰️ *Estado del Sistema — MetanoSRGAN Elite v{version}*\n\n"
        f"{sys_icon} Sistema: `{sys_status}`\n"
        f"{api_icon} API Server: `{api_status.get('status', 'offline')}`\n"
        f"📡 Fuente: {data_source}\n\n"
        f"⏱️ Última ejecución: `{last_exec}`\n"
        f"⏭️ Próximo ciclo: `{next_check}`\n\n"
    )

    if last_results:
        alertas = last_results.get("total_alertas", 0)
        criticas = last_results.get("alertas_criticas_elite_score_80", 0)
        score_max = last_results.get("elite_score_maximo", 0)
        perdida = last_results.get("perdida_total_usd_dia", 0)
        co2e = last_results.get("impacto_co2e_anual_ton", 0)

        msg += (
            f"📊 *Último Ciclo:*\n"
            f"├ Alertas totales: `{alertas}`\n"
            f"├ Alertas críticas (≥80): `{criticas}`\n"
            f"├ Elite Score máximo: `{score_max:.1f}`\n"
            f"├ Pérdida estimada: `${perdida:.2f} USD/día`\n"
            f"└ Impacto CO₂e: `{co2e:.1f} ton/año`\n"
        )

    # Suscriptores activos
    subs = load_subscribers()
    msg += f"\n👥 Suscriptores activos: `{len(subs)}`"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="estado"),
            InlineKeyboardButton("🔍 Ver Detecciones", callback_data="detecciones"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_detecciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /detecciones — Últimas detecciones."""
    dets = get_detections_combined(limit=5)

    if not dets:
        msg = "⚠️ No hay detecciones disponibles en este momento.\n\nEl sistema puede estar en ciclo de espera."
    else:
        msg = f"🔍 *Últimas {len(dets)} Detecciones — Magdalena Medio*\n\n"
        for i, det in enumerate(dets, 1):
            msg += format_detection(det, i) + "\n\n"
        msg += f"_Actualizado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC_"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="detecciones"),
            InlineKeyboardButton("🚨 Ver Críticas", callback_data="alerta"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /alerta — Detecciones críticas (Elite Score ≥ 80)."""
    all_dets = get_detections_combined(limit=50)

    # Filtrar críticas
    criticas = [
        d for d in all_dets
        if float(d.get("elite_score") or d.get("score_prioridad") or 0) >= 80
    ]

    if not criticas:
        # Mostrar las de mayor score aunque no lleguen a 80
        all_sorted = sorted(
            all_dets,
            key=lambda x: float(x.get("elite_score") or x.get("score_prioridad") or 0),
            reverse=True,
        )
        top = all_sorted[:3]
        if top:
            msg = (
                "ℹ️ *No hay alertas críticas activas (Elite Score ≥ 80)*\n\n"
                f"🟡 *Top 3 detecciones más altas:*\n\n"
            )
            for i, det in enumerate(top, 1):
                msg += format_detection(det, i) + "\n\n"
        else:
            msg = "✅ *Sistema limpio — No hay alertas activas en este momento.*"
    else:
        msg = f"🚨 *{len(criticas)} ALERTA(S) CRÍTICA(S) — Elite Score ≥ 80*\n\n"
        for i, det in enumerate(criticas[:5], 1):
            msg += format_detection(det, i) + "\n\n"
        if len(criticas) > 5:
            msg += f"_... y {len(criticas) - 5} alertas críticas más._\n"
        msg += f"\n_Actualizado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC_"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="alerta"),
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /resumen — Resumen ejecutivo del ciclo actual."""
    report = get_latest_report()
    status = get_ia_status()

    if not report and not status:
        msg = "⚠️ No hay datos de resumen disponibles."
    else:
        last_results = status.get("last_results", {})
        version = status.get("version", "3.8")
        last_exec = status.get("last_execution", "—")
        if last_exec and last_exec != "—":
            try:
                last_exec = last_exec[:16].replace("T", " ")
            except Exception:
                pass

        alertas = last_results.get("total_alertas", 0)
        criticas = last_results.get("alertas_criticas_elite_score_80", 0)
        score_max = last_results.get("elite_score_maximo", 0)
        perdida = last_results.get("perdida_total_usd_dia", 0)
        co2e = last_results.get("impacto_co2e_anual_ton", 0)

        # Datos del reporte si existen
        detecciones_report = report.get("detecciones", []) if report else []
        activo_critico = "—"
        if detecciones_report:
            top = max(
                detecciones_report,
                key=lambda x: float(x.get("elite_score") or x.get("score_prioridad") or 0),
                default=None,
            )
            if top:
                activo_critico = top.get("nombre") or top.get("activo_cercano") or "—"
        elif score_max > 0:
            # Buscar en tabla maestra
            events = get_event_master_table()
            if events:
                top = max(events, key=lambda x: float(x.get("score_prioridad", 0)), default=None)
                if top:
                    activo_critico = top.get("nombre") or "—"

        msg = (
            f"📋 *Resumen Ejecutivo — MetanoSRGAN Elite v{version}*\n"
            f"📅 Ciclo: `{last_exec}`\n\n"
            f"📊 *Métricas del Ciclo:*\n"
            f"├ Alertas detectadas: `{alertas}`\n"
            f"├ Alertas críticas (≥80): `{criticas}`\n"
            f"├ Elite Score máximo: `{score_max:.1f}`\n"
            f"├ Activo más crítico: *{activo_critico}*\n"
            f"├ Pérdida total: `${perdida:.2f} USD/día`\n"
            f"└ Impacto climático: `{co2e:.1f} ton CO₂e/año`\n\n"
            f"🌍 *Cobertura:* Magdalena Medio, Colombia\n"
            f"🛰️ *Fuente:* Copernicus Sentinel-5P TROPOMI\n"
            f"🔬 *Resolución:* 10 metros (Super-Resolución SRGAN)\n"
            f"⚙️ *Activos monitoreados:* 10\n\n"
            f"_Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC_"
        )

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="resumen"),
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_activos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /activos — Lista de activos monitoreados."""
    activos = [
        {"nombre": "Galán (TGI)", "tipo": "Estación de Compresión", "operador": "TGI", "lat": 6.8833, "lon": -73.7333},
        {"nombre": "Barrancabermeja", "tipo": "Refinería", "operador": "Ecopetrol", "lat": 7.065, "lon": -73.850},
        {"nombre": "Cantagallo", "tipo": "Campo Petrolero", "operador": "Ecopetrol", "lat": 7.383, "lon": -73.950},
        {"nombre": "San Pablo", "tipo": "Oleoducto", "operador": "Cenit", "lat": 7.500, "lon": -73.917},
        {"nombre": "Yondó", "tipo": "Campo Petrolero", "operador": "Ecopetrol", "lat": 6.833, "lon": -74.083},
        {"nombre": "Puerto Wilches", "tipo": "Terminal Fluvial", "operador": "Ecopetrol", "lat": 7.350, "lon": -73.900},
        {"nombre": "Simití", "tipo": "Gasoducto", "operador": "TGI", "lat": 7.967, "lon": -73.950},
        {"nombre": "Aguachica", "tipo": "Planta de Gas", "operador": "Vopak", "lat": 8.300, "lon": -73.617},
        {"nombre": "Gamarra", "tipo": "Estación Bombeo", "operador": "Cenit", "lat": 8.333, "lon": -73.733},
        {"nombre": "El Centro", "tipo": "Campo Petrolero", "operador": "Ecopetrol", "lat": 7.100, "lon": -73.800},
    ]

    msg = "🏭 *Activos Monitoreados — Magdalena Medio*\n\n"
    for i, a in enumerate(activos, 1):
        msg += (
            f"`{i:02d}.` *{a['nombre']}*\n"
            f"    ├ Tipo: {a['tipo']}\n"
            f"    ├ Operador: {a['operador']}\n"
            f"    └ Coords: `{a['lat']}, {a['lon']}`\n\n"
        )

    msg += f"_Total: {len(activos)} activos · Cobertura 24/7_"

    keyboard = [
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /tickets — Últimos tickets de intervención."""
    tickets = []

    # Intentar desde API
    try:
        resp = requests.get(f"{API_BASE}/api/tickets?limit=5", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            tickets = data.get("tickets", [])
    except Exception:
        pass

    # Fallback: leer archivos locales
    if not tickets and TICKETS_DIR.exists():
        for tf in sorted(TICKETS_DIR.glob("ticket_*.json"), reverse=True)[:5]:
            try:
                with open(tf) as f:
                    tickets.append(json.load(f))
            except Exception:
                pass

    if not tickets:
        msg = "📋 *Tickets de Intervención*\n\nNo hay tickets generados aún.\nLos tickets se crean automáticamente cuando Elite Score ≥ 80."
    else:
        msg = f"📋 *Últimos {len(tickets)} Tickets de Intervención*\n\n"
        for i, t in enumerate(tickets, 1):
            tid = t.get("ticket_id", t.get("id", f"TKT-{i:03d}"))[:12]
            nombre = t.get("nombre") or t.get("activo") or "—"
            score = float(t.get("elite_score") or t.get("score_prioridad") or 0)
            prioridad = t.get("prioridad") or ("CRÍTICA" if score >= 80 else "ALTA")
            fecha = t.get("fecha_generacion") or t.get("timestamp") or "—"
            if fecha and fecha != "—":
                try:
                    fecha = fecha[:10]
                except Exception:
                    pass
            estado = t.get("estado") or "PENDIENTE"
            emoji = "🔴" if prioridad == "CRÍTICA" else "🟠"

            msg += (
                f"{emoji} *Ticket #{i} — {nombre}*\n"
                f"├ ID: `{tid}...`\n"
                f"├ Elite Score: `{score:.1f}`\n"
                f"├ Prioridad: `{prioridad}`\n"
                f"├ Estado: `{estado}`\n"
                f"└ Fecha: `{fecha}`\n\n"
            )

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="tickets"),
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_mapa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /mapa — Enlace al dashboard."""
    msg = (
        "🗺️ *Dashboard MetanoSRGAN Elite v3.8*\n\n"
        "Accede al dashboard web con mapa satelital Mapbox:\n\n"
        "🌐 *Dashboard Local:*\n"
        "`http://localhost:8000`\n\n"
        "🔑 *Credenciales:*\n"
        "├ Usuario: `admin`\n"
        "└ Contraseña: `MetanoElite2026!`\n\n"
        "📊 *Funcionalidades del Dashboard:*\n"
        "├ Mapa satelital Mapbox con plumas de metano\n"
        "├ Detecciones en tiempo real\n"
        "├ Análisis ML de persistencia\n"
        "├ Datos TROPOMI Copernicus\n"
        "├ Gestión de tickets\n"
        "└ Historial de eventos\n\n"
        "☁️ *Base de Datos:* Supabase PostgreSQL\n"
        "_Datos sincronizados en tiempo real_"
    )

    keyboard = [
        [InlineKeyboardButton("🌐 Abrir Dashboard", url="http://localhost:8000")],
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def cmd_suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /suscribir — Activar alertas."""
    chat_id = update.effective_chat.id
    is_new = add_subscriber(chat_id)
    if is_new:
        msg = (
            "✅ *¡Suscrito exitosamente!*\n\n"
            "Recibirás alertas automáticas cuando se detecten emisiones críticas "
            "de metano (Elite Score ≥ 80) en el Magdalena Medio.\n\n"
            "Usa /cancelar para desactivar las alertas."
        )
    else:
        msg = "ℹ️ Ya estás suscrito. Usa /cancelar para desactivar las alertas."

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancelar — Desactivar alertas."""
    chat_id = update.effective_chat.id
    was_sub = remove_subscriber(chat_id)
    if was_sub:
        msg = (
            "🔕 *Alertas desactivadas.*\n\n"
            "Ya no recibirás notificaciones automáticas.\n"
            "Usa /suscribir para reactivarlas en cualquier momento."
        )
    else:
        msg = "ℹ️ No estabas suscrito. Usa /suscribir para activar las alertas."

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda — Ayuda completa."""
    msg = (
        "🛰️ *MetanoAlerts Bot — Ayuda Completa*\n\n"
        "*¿Qué es MetanoSRGAN Elite?*\n"
        "Sistema de detección de emisiones de metano por satélite usando "
        "Inteligencia Artificial y datos Copernicus Sentinel-5P TROPOMI. "
        "Monitorea 10 activos críticos en el Magdalena Medio, Colombia.\n\n"
        "*Comandos:*\n\n"
        "📊 `/estado` — Estado del sistema, última ejecución, métricas del ciclo\n\n"
        "🔍 `/detecciones` — Las 5 últimas detecciones de metano con métricas completas\n\n"
        "🚨 `/alerta` — Detecciones críticas con Elite Score ≥ 80 (requieren intervención)\n\n"
        "📋 `/resumen` — Resumen ejecutivo del ciclo de monitoreo actual\n\n"
        "🏭 `/activos` — Lista completa de los 10 activos monitoreados\n\n"
        "📝 `/tickets` — Tickets de intervención generados automáticamente\n\n"
        "🗺️ `/mapa` — Enlace al dashboard web con mapa satelital Mapbox\n\n"
        "🔔 `/suscribir` — Activar alertas automáticas\n\n"
        "🔕 `/cancelar` — Desactivar alertas automáticas\n\n"
        "*Elite Score:*\n"
        "🔴 ≥ 80 — Crítico (ticket automático + alerta)\n"
        "🟠 60-79 — Alto\n"
        "🟡 40-59 — Medio\n"
        "🟢 < 40 — Bajo\n\n"
        "*Fuentes de datos:*\n"
        "• Copernicus Sentinel-5P TROPOMI (ESA)\n"
        "• Open-Meteo (meteorología)\n"
        "• Supabase PostgreSQL (persistencia)\n\n"
        "_MetanoSRGAN Elite v3.9 · Magdalena Medio, Colombia_"
    )

    keyboard = [
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
        ],
        [
            InlineKeyboardButton("🚨 Alertas", callback_data="alerta"),
            InlineKeyboardButton("📋 Resumen", callback_data="resumen"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# ─── Callback Query Handler ───────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones inline."""
    query = update.callback_query
    await query.answer()

    handlers = {
        "estado": cmd_estado,
        "detecciones": cmd_detecciones,
        "alerta": cmd_alerta,
        "resumen": cmd_resumen,
        "activos": cmd_activos,
        "tickets": cmd_tickets,
        "mapa": cmd_mapa,
    }

    handler = handlers.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await query.edit_message_text("⚠️ Acción no reconocida.")


# ─── Jobs Automáticos ─────────────────────────────────────────────────────────

# Estado previo para detectar nuevas alertas
_prev_detections_ids: set = set()


async def job_check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Job periódico: verifica nuevas detecciones críticas y notifica suscriptores."""
    global _prev_detections_ids

    subs = load_subscribers()
    if not subs:
        return

    dets = get_detections_combined(limit=20)
    criticas = [
        d for d in dets
        if float(d.get("elite_score") or d.get("score_prioridad") or 0) >= ELITE_SCORE_THRESHOLD
    ]

    if not criticas:
        return

    # Detectar nuevas (por ID o timestamp)
    new_alerts = []
    for det in criticas:
        det_id = (
            det.get("id")
            or det.get("ticket_id")
            or det.get("timestamp")
            or str(det.get("nombre", "")) + str(det.get("elite_score", ""))
        )
        if det_id not in _prev_detections_ids:
            new_alerts.append(det)
            _prev_detections_ids.add(det_id)

    if not new_alerts:
        return

    # Construir mensaje de alerta
    for det in new_alerts[:3]:  # Máximo 3 alertas por ciclo
        nombre = det.get("nombre") or det.get("activo_cercano") or "Activo"
        score = float(det.get("elite_score") or det.get("score_prioridad") or 0)
        ch4 = float(det.get("ch4_ppb_total") or det.get("intensidad_ppb") or 0)
        anomaly = float(det.get("ch4_ppb_anomaly") or max(0, ch4 - 1920))
        perdida = float(det.get("perdida_usd_dia") or 0)
        co2e = float(det.get("co2e_ton_year") or 0)

        alert_msg = (
            f"🚨 *ALERTA METANO — {nombre}*\n\n"
            f"🔴 Elite Score: `{score:.1f}` ({'CRÍTICO' if score >= 80 else 'ALTO'})\n"
            f"📡 CH₄: `{ch4:.1f} ppb` (+{anomaly:.1f} ppb anomalía)\n"
            f"💰 Pérdida: `${perdida:.2f} USD/día`\n"
            f"🌍 CO₂e: `{co2e:.1f} ton/año`\n\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"📍 Magdalena Medio, Colombia\n\n"
            f"_Usa /detecciones para más detalles_"
        )

        keyboard = [
            [
                InlineKeyboardButton("🔍 Ver Detecciones", callback_data="detecciones"),
                InlineKeyboardButton("📊 Estado", callback_data="estado"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        for chat_id in subs:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=alert_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup,
                )
                logger.info(f"Alerta enviada a {chat_id}: {nombre} (score={score:.1f})")
            except Exception as e:
                logger.warning(f"Error enviando alerta a {chat_id}: {e}")


async def job_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Job diario: envía resumen a todos los suscriptores a las 08:00 Colombia."""
    subs = load_subscribers()
    if not subs:
        return

    status = get_ia_status()
    last_results = status.get("last_results", {})
    version = status.get("version", "3.8")

    alertas = last_results.get("total_alertas", 0)
    criticas = last_results.get("alertas_criticas_elite_score_80", 0)
    score_max = last_results.get("elite_score_maximo", 0)
    perdida = last_results.get("perdida_total_usd_dia", 0)
    co2e = last_results.get("impacto_co2e_anual_ton", 0)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    msg = (
        f"☀️ *Resumen Diario — MetanoSRGAN Elite v{version}*\n"
        f"📅 {today}\n\n"
        f"📊 *Métricas del día:*\n"
        f"├ Alertas detectadas: `{alertas}`\n"
        f"├ Alertas críticas: `{criticas}`\n"
        f"├ Elite Score máximo: `{score_max:.1f}`\n"
        f"├ Pérdida estimada: `${perdida:.2f} USD/día`\n"
        f"└ Impacto CO₂e: `{co2e:.1f} ton/año`\n\n"
        f"🛰️ Sistema operativo 24/7 · Magdalena Medio, Colombia\n"
        f"_Usa /detecciones para ver detalles completos_"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔍 Detecciones", callback_data="detecciones"),
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in subs:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.warning(f"Error enviando resumen diario a {chat_id}: {e}")

    logger.info(f"Resumen diario enviado a {len(subs)} suscriptores")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Inicia el bot de Telegram."""
    logger.info("=" * 60)
    logger.info("MetanoAlerts Bot — MetanoSRGAN Elite v3.9")
    logger.info("Bot: @MetanoAlerts_bot")
    logger.info("=" * 60)

    # Cargar .env si existe
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
        logger.info("Variables de entorno cargadas desde .env")

    # Crear aplicación
    app = Application.builder().token(BOT_TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("detecciones", cmd_detecciones))
    app.add_handler(CommandHandler("alerta", cmd_alerta))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("activos", cmd_activos))
    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("mapa", cmd_mapa))
    app.add_handler(CommandHandler("suscribir", cmd_suscribir))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("help", cmd_ayuda))

    # Callback queries (botones inline)
    app.add_handler(CallbackQueryHandler(button_callback))

    # Jobs automáticos
    job_queue = app.job_queue

    # Verificar alertas cada 15 minutos
    job_queue.run_repeating(
        job_check_alerts,
        interval=900,  # 15 minutos
        first=30,      # Primera ejecución en 30 segundos
        name="check_alerts",
    )

    # Resumen diario a las 08:00 UTC-5 (Colombia) = 13:00 UTC
    job_queue.run_daily(
        job_daily_summary,
        time=datetime.strptime("13:00", "%H:%M").replace(tzinfo=timezone.utc).timetz(),
        name="daily_summary",
    )

    logger.info("Bot iniciado. Esperando mensajes...")
    logger.info(f"Suscriptores activos: {len(load_subscribers())}")
    logger.info("Jobs: check_alerts (15min), daily_summary (08:00 COT)")

    # Iniciar polling
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
