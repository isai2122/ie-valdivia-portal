"""
enhancements_v55.py — MetanoSRGAN Elite v5.5
==============================================
Módulo de mejoras "Mata-Gigantes" que añade funcionalidad de clase enterprise
sobre la base v5.4 sin alterar el comportamiento existente.

Características:
  1. Calculadora de Créditos de Carbono (Verra VM0033, Gold Standard, ART TREES)
     usando GWP IPCC AR6 = 29.8 (CH4 → CO2e a 100 años)
  2. Compliance Tracker — EPA OOOOa/b, EU MRR, Colombia RUA-PI, OGMP 2.0
  3. Exportadores: CSV, Excel (xlsx), PDF (reportlab)
  4. Sistema de API Keys públicas con scopes y rate-limit por key
  5. Webhooks salientes registrables (SCADA / ERP / MS Teams / Slack)
  6. Comparativas históricas (semana, mes, año) por activo
  7. Hash-chain de auditoría (cadena tipo blockchain) para inmutabilidad

Constantes oficiales:
  - GWP_CH4_AR6 = 29.8     (IPCC AR6, 100 años, fossil)
  - GWP_CH4_AR6_20Y = 82.5 (IPCC AR6, 20 años, fossil — métrica EU MRR)
  - PRECIO_CARBONO_VERRA   ~ 5.5 USD/tCO2e (mercado voluntario 2025)
  - PRECIO_CARBONO_EU_ETS  ~ 75 USD/tCO2e  (cap-and-trade UE)
  - DENSIDAD_CH4_STP       = 0.668 kg/m³
"""
import os
import io
import csv
import json
import hmac
import time
import uuid
import hashlib
import logging
import secrets
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
GWP_CH4_AR6_100Y = 29.8
GWP_CH4_AR6_20Y  = 82.5
DENSIDAD_CH4_KG_M3 = 0.668     # densidad CH4 a 0°C, 1 atm
PRECIO_VERRA_USD   = 5.5       # USD por tCO2e (voluntario)
PRECIO_GOLD_USD    = 11.0      # USD por tCO2e (Gold Standard)
PRECIO_EU_ETS_USD  = 75.0      # USD por tCO2e (EUA spot 2025)
PRECIO_CALIFORNIA_USD = 32.0   # USD por tCO2e (CARB)


# ─── 1. Calculadora de Créditos de Carbono ──────────────────────────────────
class CarbonCreditCalculator:
    """
    Calcula créditos de carbono y valor económico equivalente
    para una emisión de metano detectada.

    Inputs típicos:
        ch4_ppb_anomaly: anomalía de CH4 sobre baseline (ppb)
        wind_speed_ms:   velocidad del viento (m/s)
        radio_pluma_km:  extensión de la pluma (km)
        duracion_horas:  tiempo estimado de emisión (h)
    """

    @staticmethod
    def ppb_to_kg_per_hour(
        ch4_ppb_anomaly: float,
        wind_speed_ms: float = 3.0,
        area_km2: float = 1.0,
    ) -> float:
        """
        Convierte una anomalía de columna CH4 (ppb) a kg/h emitidos
        usando un modelo simple de divergencia de masa (Jacob et al. 2016).

        Formula: Q = (V_column × A × v) donde V_column ≈ ppb × factor
        """
        # Conversión simplificada: 1 ppb ≈ 7.5e-9 mol/m² para columna troposférica
        mol_m2 = ch4_ppb_anomaly * 7.5e-9
        # Tasa de transporte por viento × área expuesta (perímetro)
        perimetro_m = 2 * 3.14159 * (area_km2 * 1e6) ** 0.5
        flujo_mol_s = mol_m2 * perimetro_m * wind_speed_ms
        # Mol → kg (CH4 = 16.043 g/mol)
        kg_h = flujo_mol_s * 0.016043 * 3600
        return max(0.0, kg_h)

    @classmethod
    def calc_co2e_anual(
        cls,
        ch4_kg_h: float,
        gwp: float = GWP_CH4_AR6_100Y,
        duracion_dias: int = 365,
    ) -> Dict[str, float]:
        """
        Calcula CO2 equivalente anual y créditos potenciales.
        """
        ch4_ton_year = ch4_kg_h * 24 * duracion_dias / 1000.0
        co2e_ton_year = ch4_ton_year * gwp
        return {
            "ch4_ton_year": round(ch4_ton_year, 3),
            "co2e_ton_year": round(co2e_ton_year, 2),
            "creditos_verra_usd": round(co2e_ton_year * PRECIO_VERRA_USD, 2),
            "creditos_gold_standard_usd": round(co2e_ton_year * PRECIO_GOLD_USD, 2),
            "valor_eu_ets_usd": round(co2e_ton_year * PRECIO_EU_ETS_USD, 2),
            "valor_carb_california_usd": round(co2e_ton_year * PRECIO_CALIFORNIA_USD, 2),
            "gwp_aplicado": gwp,
            "metodologia": "IPCC AR6 (100y) — Verra VM0033 / GS Methane Recovery",
        }

    @classmethod
    def from_detection(cls, detection: Dict) -> Dict:
        """Calcula créditos a partir de un evento de detección."""
        ppb_anom = detection.get("ch4_ppb_anomaly",
                                  detection.get("intensidad_ppb", 0) - 1920)
        wind = detection.get("viento_dominante_velocidad",
                             detection.get("wind_speed", 3.0))
        area = detection.get("area_pluma_km2", 1.0)
        kg_h = cls.ppb_to_kg_per_hour(ppb_anom, wind, area)
        result = cls.calc_co2e_anual(kg_h)
        result["ch4_kg_per_hour"] = round(kg_h, 2)
        result["activo"] = detection.get("activo_cercano", "")
        result["fecha_calculo"] = datetime.now(timezone.utc).isoformat()
        return result


# ─── 2. Compliance Tracker ──────────────────────────────────────────────────
class ComplianceTracker:
    """
    Evalúa cada detección contra normativas internacionales y locales:

    - EPA NSPS OOOOa/b (US)        — umbral 100 kg CH4/h en oil & gas
    - EU MRR (Methane Regulation)  — umbral 7 kg/h reportable
    - Colombia RUA-PI (ANLA)       — reporte mensual + SIRH-CH4
    - OGMP 2.0 (UNEP) Gold tier    — empresas con compromiso climate
    - Banco Mundial GMFR           — umbral 25 kg/h flaring
    """

    NORMATIVAS = {
        "epa_ooooa_b": {
            "nombre": "EPA NSPS Subpart OOOOa / OOOOb (USA)",
            "limite_kg_h": 100.0,
            "limite_lb_year": 200_000,
            "autoridad": "U.S. Environmental Protection Agency",
            "url": "https://www.epa.gov/controlling-air-pollution-oil-and-natural-gas-operations",
            "color": "#1f77b4",
        },
        "eu_mrr": {
            "nombre": "EU Methane Regulation 2024/1787",
            "limite_kg_h": 7.0,
            "fecha_vigencia": "2024-08-04",
            "autoridad": "European Commission DG ENER",
            "url": "https://eur-lex.europa.eu/eli/reg/2024/1787/oj",
            "color": "#003399",
        },
        "co_rua_pi": {
            "nombre": "RUA-PI / SIRH-CH4 (Colombia)",
            "limite_kg_h": 50.0,
            "autoridad": "ANLA — Ministerio de Ambiente",
            "url": "https://www.anla.gov.co",
            "color": "#FCD116",
        },
        "ogmp_2_0_gold": {
            "nombre": "OGMP 2.0 — Gold Tier (UNEP)",
            "limite_kg_h": 5.0,
            "autoridad": "United Nations Environment Programme",
            "url": "https://www.unep.org/oil-and-gas-methane-partnership",
            "color": "#fcc419",
        },
        "wb_gmfr": {
            "nombre": "World Bank Global Methane Flaring Reduction",
            "limite_kg_h": 25.0,
            "autoridad": "World Bank",
            "url": "https://www.worldbank.org/en/programs/gasflaringreduction",
            "color": "#00ad4d",
        },
    }

    @classmethod
    def evaluate(cls, ch4_kg_h: float) -> List[Dict]:
        """Devuelve estado de cumplimiento contra cada normativa."""
        out = []
        for key, norm in cls.NORMATIVAS.items():
            limite = norm["limite_kg_h"]
            excede = ch4_kg_h > limite
            ratio = ch4_kg_h / limite if limite else 0
            out.append({
                "normativa_id": key,
                "nombre":       norm["nombre"],
                "autoridad":    norm["autoridad"],
                "url":          norm["url"],
                "color":        norm["color"],
                "limite_kg_h":  limite,
                "emision_kg_h": round(ch4_kg_h, 2),
                "ratio":        round(ratio, 2),
                "estado":       "EXCEDE" if excede else "CUMPLE",
                "severidad":    ("CRÍTICA" if ratio > 5 else "ALTA" if ratio > 2 else "MEDIA")
                                if excede else "OK",
            })
        return out

    @classmethod
    def summary(cls, detections: List[Dict]) -> Dict:
        """Resumen de cumplimiento de un lote de detecciones."""
        by_norm = {k: {"total": 0, "excede": 0, "cumple": 0} for k in cls.NORMATIVAS}
        for det in detections:
            ppb_anom = det.get("ch4_ppb_anomaly", 0)
            wind = det.get("viento_dominante_velocidad", 3.0)
            kg_h = CarbonCreditCalculator.ppb_to_kg_per_hour(ppb_anom, wind)
            for ev in cls.evaluate(kg_h):
                k = ev["normativa_id"]
                by_norm[k]["total"] += 1
                if ev["estado"] == "EXCEDE":
                    by_norm[k]["excede"] += 1
                else:
                    by_norm[k]["cumple"] += 1
        for k, v in by_norm.items():
            v["nombre"] = cls.NORMATIVAS[k]["nombre"]
            v["color"] = cls.NORMATIVAS[k]["color"]
            v["pct_cumplimiento"] = round(
                100.0 * v["cumple"] / v["total"], 1
            ) if v["total"] else 100.0
        return {
            "evaluado_en": datetime.now(timezone.utc).isoformat(),
            "total_detecciones": len(detections),
            "por_normativa": by_norm,
        }


# ─── 3. Exportadores ────────────────────────────────────────────────────────
class Exporter:
    """Genera CSV, Excel y PDF de detecciones."""

    @staticmethod
    def to_csv(detections: List[Dict]) -> bytes:
        if not detections:
            return b"sin datos\n"
        keys = sorted({k for d in detections for k in d.keys()})
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for d in detections:
            row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                   for k, v in d.items()}
            w.writerow(row)
        return out.getvalue().encode("utf-8")

    @staticmethod
    def to_excel(detections: List[Dict]) -> bytes:
        try:
            from openpyxl import Workbook
        except ImportError:
            return Exporter.to_csv(detections)
        wb = Workbook()
        ws = wb.active
        ws.title = "Detecciones"
        if not detections:
            ws.append(["sin datos"])
        else:
            keys = ["fecha_deteccion", "activo_cercano", "operador", "tipo_activo",
                    "latitud", "longitud", "intensidad_ppb", "ch4_ppb_anomaly",
                    "score_prioridad", "categoria_alerta", "perdida_economica_usd_dia"]
            ws.append(keys)
            for d in detections:
                ws.append([d.get(k, "") for k in keys])
            # Ancho columnas
            for col_idx, key in enumerate(keys, 1):
                ws.column_dimensions[chr(64 + col_idx)].width = max(14, len(key) + 2)
        # Hoja de resumen
        ws2 = wb.create_sheet("Resumen Compliance")
        cs = ComplianceTracker.summary(detections)
        ws2.append(["Normativa", "Total", "Cumple", "Excede", "% Cumplimiento"])
        for k, v in cs["por_normativa"].items():
            ws2.append([v["nombre"], v["total"], v["cumple"], v["excede"], v["pct_cumplimiento"]])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def to_pdf(detections: List[Dict], title: str = "MetanoSRGAN Elite — Reporte") -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            )
        except ImportError:
            return b"reportlab no disponible"

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=landscape(A4),
            leftMargin=1.2 * cm, rightMargin=1.2 * cm,
            topMargin=1 * cm, bottomMargin=1 * cm,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                            textColor=colors.HexColor("#00d4ff"))
        story = [
            Paragraph(f"<b>{title}</b>", h1),
            Paragraph(
                f"Generado: {datetime.now(timezone.utc).isoformat()}<br/>"
                f"Detecciones: {len(detections)} • Zona: Magdalena Medio, Colombia<br/>"
                f"Fuente: Copernicus Sentinel-5P TROPOMI + Open-Meteo",
                styles["Normal"]
            ),
            Spacer(1, 0.5 * cm),
        ]

        # Tabla principal
        headers = ["Fecha", "Activo", "Operador", "CH4 ppb", "Anom ppb",
                   "Score", "Categoría", "Pérdida USD/día"]
        rows = [headers]
        for d in detections[:100]:  # limitar para PDF
            rows.append([
                str(d.get("fecha_deteccion", ""))[:10],
                d.get("activo_cercano", "")[:18],
                d.get("operador", "")[:14],
                str(round(d.get("intensidad_ppb", d.get("ch4_ppb_total", 0)), 1)),
                str(round(d.get("ch4_ppb_anomaly", 0), 1)),
                str(round(d.get("score_prioridad", d.get("elite_score", 0)), 1)),
                d.get("categoria_alerta", "")[:12],
                f"${d.get('perdida_economica_usd_dia', 0):,.0f}",
            ])
        t = Table(rows, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1b2e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#00d4ff")),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#1e3a5f")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f5f9ff")]),
        ]))
        story.append(t)

        # Resumen Compliance
        story.append(PageBreak())
        story.append(Paragraph("<b>Resumen de Cumplimiento</b>", h1))
        cs = ComplianceTracker.summary(detections)
        head = ["Normativa", "Total", "Cumple", "Excede", "% Cumplimiento"]
        rows = [head]
        for k, v in cs["por_normativa"].items():
            rows.append([v["nombre"], v["total"], v["cumple"], v["excede"],
                         f"{v['pct_cumplimiento']}%"])
        t2 = Table(rows, hAlign="LEFT")
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1b2e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#1e3a5f")),
        ]))
        story.append(t2)

        doc.build(story)
        buf.seek(0)
        return buf.read()


# ─── 4. API Keys públicas ────────────────────────────────────────────────────
class ApiKeyManager:
    """Gestor de API Keys con scopes y rate-limit por key."""

    SCOPES = ["read:detections", "read:stats", "read:compliance",
              "write:webhook", "admin:keys"]

    def __init__(self, storage_file: str):
        self.file = Path(storage_file)
        self._keys: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                self._keys = json.loads(self.file.read_text())
            except Exception:
                self._keys = {}

    def _save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._keys, indent=2, default=str))

    def create(self, owner: str, scopes: List[str], name: str = "default",
               rate_limit_per_min: int = 60) -> Dict:
        token = "msr_" + secrets.token_urlsafe(32)
        info = {
            "key": token,
            "owner": owner,
            "name": name,
            "scopes": [s for s in scopes if s in self.SCOPES],
            "rate_limit_per_min": rate_limit_per_min,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
            "last_used": None,
            "use_count": 0,
        }
        with self._lock:
            self._keys[token] = info
            self._save()
        return info

    def list_by_owner(self, owner: str) -> List[Dict]:
        return [
            {**v, "key": v["key"][:12] + "..." + v["key"][-6:]}
            for v in self._keys.values() if v.get("owner") == owner
        ]

    def list_all(self) -> List[Dict]:
        return [
            {**v, "key": v["key"][:12] + "..." + v["key"][-6:]}
            for v in self._keys.values()
        ]

    def verify(self, token: str, required_scope: Optional[str] = None) -> Optional[Dict]:
        info = self._keys.get(token)
        if not info or not info.get("active"):
            return None
        if required_scope and required_scope not in info.get("scopes", []):
            return None
        with self._lock:
            info["last_used"] = datetime.now(timezone.utc).isoformat()
            info["use_count"] = info.get("use_count", 0) + 1
            self._save()
        return info

    def revoke(self, token_or_prefix: str) -> bool:
        with self._lock:
            for k, v in list(self._keys.items()):
                if k == token_or_prefix or k.startswith(token_or_prefix):
                    v["active"] = False
                    v["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return True
        return False


# ─── 5. Webhooks salientes ───────────────────────────────────────────────────
class WebhookManager:
    """Permite registrar URLs externas (SCADA, ERP, Slack, MS Teams) que
    reciben POST cuando ocurre un evento crítico."""

    EVENTS = ["detection.created", "detection.elite", "compliance.violation",
              "ml.prediction.high_risk", "system.alert"]

    def __init__(self, storage_file: str):
        self.file = Path(storage_file)
        self._hooks: List[Dict] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                self._hooks = json.loads(self.file.read_text())
            except Exception:
                self._hooks = []

    def _save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._hooks, indent=2, default=str))

    def register(self, owner: str, url: str, events: List[str],
                 secret: Optional[str] = None, name: str = "default") -> Dict:
        hook = {
            "id": str(uuid.uuid4())[:8],
            "owner": owner,
            "name": name,
            "url": url,
            "events": [e for e in events if e in self.EVENTS],
            "secret": secret or secrets.token_urlsafe(24),
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "delivered": 0,
            "failed": 0,
            "last_delivery": None,
        }
        with self._lock:
            self._hooks.append(hook)
            self._save()
        return hook

    def list_by_owner(self, owner: str) -> List[Dict]:
        return [h for h in self._hooks if h.get("owner") == owner]

    def list_all(self) -> List[Dict]:
        return self._hooks

    def delete(self, hook_id: str) -> bool:
        with self._lock:
            before = len(self._hooks)
            self._hooks = [h for h in self._hooks if h["id"] != hook_id]
            if len(self._hooks) != before:
                self._save()
                return True
        return False

    async def fire(self, event: str, payload: Dict):
        """Dispara webhooks suscritos a este evento."""
        try:
            import httpx
        except ImportError:
            logger.warning("httpx no disponible para webhooks")
            return
        body = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body_bytes = json.dumps(body, default=str).encode()
        for hook in list(self._hooks):
            if not hook.get("active") or event not in hook.get("events", []):
                continue
            sig = hmac.new(hook["secret"].encode(), body_bytes,
                           hashlib.sha256).hexdigest()
            try:
                async with httpx.AsyncClient(timeout=5) as cli:
                    r = await cli.post(
                        hook["url"], content=body_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-MetanoSRGAN-Signature": f"sha256={sig}",
                            "X-MetanoSRGAN-Event": event,
                        },
                    )
                hook["delivered"] = hook.get("delivered", 0) + 1
                hook["last_delivery"] = datetime.now(timezone.utc).isoformat()
                hook["last_status"] = r.status_code
            except Exception as e:
                hook["failed"] = hook.get("failed", 0) + 1
                hook["last_error"] = str(e)[:200]
            finally:
                self._save()


# ─── 6. Hash-chain de auditoría ─────────────────────────────────────────────
class AuditChain:
    """Cadena de hashes encadenados (estilo blockchain) para inmutabilidad
    del log de auditoría administrativa."""

    def __init__(self, storage_file: str):
        self.file = Path(storage_file)
        self._chain: List[Dict] = []
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                self._chain = json.loads(self.file.read_text())
            except Exception:
                self._chain = []

    def _save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._chain[-2000:], indent=2, default=str))

    def append(self, action: str, actor: str, target: str, details: Any = "") -> Dict:
        prev_hash = self._chain[-1]["hash"] if self._chain else "GENESIS"
        block = {
            "index": len(self._chain),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "target": target,
            "details": details if isinstance(details, str)
                       else json.dumps(details, default=str),
            "prev_hash": prev_hash,
        }
        block_str = json.dumps(block, sort_keys=True, default=str)
        block["hash"] = hashlib.sha256(block_str.encode()).hexdigest()
        self._chain.append(block)
        self._save()
        return block

    def verify(self) -> Dict:
        broken_at = None
        for i, b in enumerate(self._chain):
            prev_hash = self._chain[i - 1]["hash"] if i > 0 else "GENESIS"
            if b.get("prev_hash") != prev_hash:
                broken_at = i
                break
            recompute = b.copy()
            h = recompute.pop("hash", "")
            block_str = json.dumps(recompute, sort_keys=True, default=str)
            if hashlib.sha256(block_str.encode()).hexdigest() != h:
                broken_at = i
                break
        return {
            "total_bloques": len(self._chain),
            "integro": broken_at is None,
            "ruptura_en_bloque": broken_at,
            "ultimo_hash": self._chain[-1]["hash"] if self._chain else None,
        }

    def tail(self, limit: int = 50) -> List[Dict]:
        return list(reversed(self._chain[-limit:]))


# ─── 7. Comparativas históricas ──────────────────────────────────────────────
class HistoricalAnalytics:
    """Genera comparativas semana/mes/año por activo."""

    @staticmethod
    def _bucket(dt_str: str, kind: str) -> str:
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return "desconocido"
        if kind == "day":
            return dt.strftime("%Y-%m-%d")
        if kind == "week":
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        if kind == "month":
            return dt.strftime("%Y-%m")
        if kind == "year":
            return dt.strftime("%Y")
        return dt.strftime("%Y-%m-%d")

    @classmethod
    def by_period(cls, detections: List[Dict], kind: str = "month") -> Dict:
        buckets: Dict[str, Dict] = {}
        for d in detections:
            key = cls._bucket(d.get("fecha_deteccion", d.get("timestamp", "")), kind)
            b = buckets.setdefault(key, {
                "periodo": key, "total": 0, "elite": 0, "critico": 0,
                "score_max": 0, "score_avg": 0, "_scores": [],
                "perdida_total_usd": 0,
            })
            score = d.get("score_prioridad", d.get("elite_score", 0)) or 0
            b["total"] += 1
            b["_scores"].append(score)
            if score >= 80: b["elite"] += 1
            elif score >= 60: b["critico"] += 1
            b["score_max"] = max(b["score_max"], score)
            b["perdida_total_usd"] += d.get("perdida_economica_usd_dia", 0) or 0
        for b in buckets.values():
            b["score_avg"] = round(sum(b["_scores"]) / len(b["_scores"]), 1) if b["_scores"] else 0
            b.pop("_scores", None)
            b["perdida_total_usd"] = round(b["perdida_total_usd"], 2)
        return {
            "kind": kind,
            "buckets": sorted(buckets.values(), key=lambda x: x["periodo"]),
        }

    @classmethod
    def by_asset(cls, detections: List[Dict]) -> Dict:
        out: Dict[str, Dict] = {}
        for d in detections:
            a = d.get("activo_cercano", "desconocido")
            row = out.setdefault(a, {
                "activo": a, "total": 0, "elite": 0, "score_max": 0,
                "score_avg": 0, "_scores": [], "perdida_total_usd": 0,
                "operador": d.get("operador", ""),
                "lat": d.get("latitud"), "lon": d.get("longitud"),
            })
            score = d.get("score_prioridad", d.get("elite_score", 0)) or 0
            row["total"] += 1
            row["_scores"].append(score)
            if score >= 80: row["elite"] += 1
            row["score_max"] = max(row["score_max"], score)
            row["perdida_total_usd"] += d.get("perdida_economica_usd_dia", 0) or 0
        for r in out.values():
            r["score_avg"] = round(sum(r["_scores"]) / len(r["_scores"]), 1) if r["_scores"] else 0
            r.pop("_scores", None)
            r["perdida_total_usd"] = round(r["perdida_total_usd"], 2)
        return {"activos": sorted(out.values(), key=lambda x: -x["score_max"])}
