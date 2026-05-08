"""
plans_v55.py — Sistema de Planes de Suscripción
================================================
Define los 3 planes disponibles, sus features, límites y precios.
Permite gating de endpoints y features por plan asignado al usuario.

Planes:
  - regional        → Monitoreo Regional       ($800/mes)
  - operacional     → Operacional Completo     ($2,500/mes)
  - enterprise      → Enterprise (Ecopetrol)   ($8,000–15,000/mes)
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone


# ─── Definición de planes ─────────────────────────────────────────────────────
PLANS: Dict[str, Dict] = {
    "regional": {
        "id": "regional",
        "nombre": "Monitoreo Regional",
        "precio_mensual_usd": 800,
        "publico_objetivo": "Operadores pequeños o empresas que quieren empezar.",
        "color": "#00d4ff",
        "icon": "◉",
        "limites": {
            "max_activos":          5,
            "max_usuarios":         2,
            "alertas_telegram":     True,
            "exports_csv":          True,
            "exports_excel":        False,
            "exports_pdf":          False,
            "compliance":           False,
            "carbon_credits":       False,
            "api_keys":             False,
            "webhooks":             False,
            "ml_predictions":       False,
            "sentinel1_sar":        False,
            "sentinel2_swir":       False,
            "anla_reports":         False,
            "elite_field_app":      False,
            "soporte_horas":        72,
        },
        "incluye": [
            "Monitoreo diario de CH4 (TROPOMI real)",
            "Alertas Telegram automáticas",
            "Dashboard web con mapa",
            "Hasta 5 activos monitoreados",
            "Hasta 2 usuarios",
        ],
        "no_incluye": [
            "Sin app móvil de campo",
            "Sin reporte regulatorio",
            "Sin créditos de carbono",
            "Sin API keys",
        ],
    },

    "operacional": {
        "id": "operacional",
        "nombre": "Operacional Completo",
        "precio_mensual_usd": 2500,
        "publico_objetivo": "Operadoras medianas. Monitoreo + campo + reportes.",
        "color": "#ff8c00",
        "icon": "◆",
        "limites": {
            "max_activos":          15,
            "max_usuarios":         5,
            "alertas_telegram":     True,
            "exports_csv":          True,
            "exports_excel":        True,
            "exports_pdf":          True,
            "compliance":           True,
            "carbon_credits":       True,
            "api_keys":             False,
            "webhooks":             True,
            "ml_predictions":       True,
            "sentinel1_sar":        True,
            "sentinel2_swir":       False,
            "anla_reports":         False,
            "elite_field_app":      True,
            "soporte_horas":        24,
        },
        "incluye": [
            "Todo del plan Regional",
            "Hasta 15 activos monitoreados",
            "Hasta 5 usuarios",
            "App EliteField para operadores",
            "Tickets de intervención automáticos",
            "Compliance Dashboard (EPA, EU MRR, etc.)",
            "Calculadora de Créditos de Carbono",
            "Predicciones ML de reincidencia",
            "Capa Sentinel-1 SAR (radar)",
            "Reporte mensual Google Sheets",
            "Webhooks salientes (Slack/Teams/SCADA)",
            "Soporte por WhatsApp/Telegram",
        ],
        "no_incluye": [
            "Sin Sentinel-2 SWIR (alta resolución)",
            "Sin reportes ANLA/Resolución 40066",
            "Sin integración SAP/SCADA enterprise",
            "Sin API keys públicas",
        ],
    },

    "enterprise": {
        "id": "enterprise",
        "nombre": "Enterprise",
        "precio_mensual_usd_min": 8000,
        "precio_mensual_usd_max": 15000,
        "precio_mensual_usd": 8000,
        "publico_objetivo": "Operadoras con decenas de activos. Confirmación con Sentinel-2 SWIR (20m reales) y documentación regulatoria ANLA.",
        "color": "#a855f7",
        "icon": "♛",
        "limites": {
            "max_activos":          -1,   # ilimitados
            "max_usuarios":         -1,
            "alertas_telegram":     True,
            "exports_csv":          True,
            "exports_excel":        True,
            "exports_pdf":          True,
            "compliance":           True,
            "carbon_credits":       True,
            "api_keys":             True,
            "webhooks":             True,
            "ml_predictions":       True,
            "sentinel1_sar":        True,
            "sentinel2_swir":       True,
            "anla_reports":         True,
            "elite_field_app":      True,
            "soporte_horas":        4,
        },
        "incluye": [
            "Activos ilimitados en Magdalena Medio",
            "Usuarios ilimitados",
            "Análisis Sentinel-2 SWIR (confirmación 20m)",
            "Reportes ANLA / Resolución 40066",
            "API Keys públicas con scopes",
            "SLA de respuesta en 4 horas",
            "Integración con SAP/SCADA",
            "Auditoría blockchain certificada",
            "Soporte 24/7 prioritario",
        ],
        "no_incluye": [],
    },
}


# Feature aliases para gating sencillo
FEATURE_GATES = {
    "carbon_credits":  ["carbon_credits"],
    "compliance":      ["compliance"],
    "ml_predictions":  ["ml_predictions"],
    "exports_pdf":     ["exports_pdf"],
    "exports_excel":   ["exports_excel"],
    "exports_csv":     ["exports_csv"],
    "api_keys":        ["api_keys"],
    "webhooks":        ["webhooks"],
    "sentinel1":       ["sentinel1_sar"],
    "sentinel2":       ["sentinel2_swir"],
    "anla_reports":    ["anla_reports"],
}


def get_plan(plan_id: str) -> Dict:
    """Devuelve la definición de un plan (o el regional por defecto)."""
    return PLANS.get(plan_id, PLANS["regional"])


def list_plans() -> List[Dict]:
    """Lista todos los planes disponibles (sin info sensible)."""
    return list(PLANS.values())


def user_has_feature(user_dict: Dict, feature_key: str) -> bool:
    """
    Verifica si un usuario tiene acceso a una feature según su plan.
    El admin siempre tiene acceso total.
    """
    if not user_dict:
        return False
    if user_dict.get("role") == "admin":
        return True
    plan_id = user_dict.get("plan", "regional")
    plan = get_plan(plan_id)
    return bool(plan.get("limites", {}).get(feature_key, False))


def user_can_add_asset(user_dict: Dict, current_count: int) -> bool:
    """Verifica si el usuario puede agregar más activos."""
    if user_dict.get("role") == "admin":
        return True
    plan = get_plan(user_dict.get("plan", "regional"))
    max_act = plan.get("limites", {}).get("max_activos", 5)
    return max_act < 0 or current_count < max_act


def user_plan_summary(user_dict: Dict) -> Dict:
    """Resumen del plan del usuario para mostrar en el dashboard."""
    if user_dict.get("role") == "admin":
        return {
            "plan_id": "admin",
            "nombre": "Administrador",
            "color": "#ff2244",
            "icon": "♛",
            "limites": {"max_activos": -1, "max_usuarios": -1},
            "todo_habilitado": True,
        }
    plan = get_plan(user_dict.get("plan", "regional"))
    return {
        "plan_id": plan["id"],
        "nombre": plan["nombre"],
        "color": plan["color"],
        "icon": plan["icon"],
        "limites": plan["limites"],
        "incluye": plan["incluye"],
        "no_incluye": plan.get("no_incluye", []),
        "soporte_horas": plan["limites"]["soporte_horas"],
        "renovacion": user_dict.get("plan_renovacion"),
    }
