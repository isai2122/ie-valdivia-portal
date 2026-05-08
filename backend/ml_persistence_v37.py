"""
ml_persistence_v37.py — MetanoSRGAN Elite v3.7
Análisis ML de persistencia de fugas: predicción de reincidencia usando
scikit-learn con datos históricos reales.
"""

import os
import json
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# ─── Verificar scikit-learn ───────────────────────────────────────────────────
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import classification_report
    import joblib
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn no disponible — usando análisis estadístico básico")

# ─── Constantes ───────────────────────────────────────────────────────────────
ELITE_THRESHOLD = 80          # Umbral para alerta ÉLITE
REINCIDENCE_DAYS = 7          # Ventana de predicción de reincidencia
MIN_EVENTS_FOR_ML = 3         # Mínimo de eventos por activo para ML
CH4_BACKGROUND_PPB = 1920.0   # Fondo global NOAA 2024

class MLPersistenceAnalyzer:
    """
    Analizador ML de persistencia de fugas de metano.
    Usa datos históricos reales para predecir reincidencia y priorizar intervenciones.
    """

    def __init__(
        self,
        data_dir: str = "/app/metanosrgan_v55/data",
        models_dir: str = "/app/metanosrgan_v55/data/ml_models",
    ):
        self.data_dir = data_dir
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)

        self.scaler = StandardScaler() if _SKLEARN_AVAILABLE else None
        self.rf_classifier = None
        self.gb_regressor = None
        self.kmeans = None
        self._trained = False

        # Cargar historial (prioridad Supabase)
        try:
            from backend.supabase_integration_v38 import db as supabase_db
            if supabase_db.is_connected():
                self.events = supabase_db.get_detections(limit=1000)
                logger.info(f"ML: Cargados {len(self.events)} eventos desde Supabase")
            else:
                self.events = self._load_events()
        except Exception as e:
            logger.warning(f"Error cargando Supabase en ML: {e}")
            self.events = self._load_events()

        logger.info(
            f"MLPersistenceAnalyzer inicializado — "
            f"sklearn: {'OK' if _SKLEARN_AVAILABLE else 'N/A'} | "
            f"Eventos históricos: {len(self.events)}"
        )

    def _load_events(self) -> List[Dict]:
        path = os.path.join(self.data_dir, "event_master_table.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else data.get("events", [])
            except Exception:
                pass
        return []

    def _extract_features(self, event: Dict) -> List[float]:
        ch4_ppb = event.get("intensidad_ppb", event.get("ch4_ppb_total", CH4_BACKGROUND_PPB))
        anomaly = event.get("ch4_ppb_anomaly", max(0, (float(ch4_ppb or 0)) - CH4_BACKGROUND_PPB))
        wind_speed = event.get("viento_dominante_velocidad", event.get("wind_speed", 2.5))
        wind_deg = event.get("viento_dominante_direccion", event.get("wind_deg", 45))
        persistencia = event.get("persistencia_dias", 1)
        elite_score = event.get("score_prioridad", event.get("elite_score", 0))
        flujo = event.get("flujo_kgh", 0.01)
        perdida = event.get("perdida_economica_usd_dia", 0.1)

        def _f(x, default=0.0):
            try: return float(x) if x is not None else float(default)
            except: return float(default)

        # Parsear fecha
        fecha_str = event.get("fecha_deteccion", "")
        try:
            fecha = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            hora, mes = fecha.hour, fecha.month
        except:
            hora, mes = 12, 4

        wind_rad = np.radians(_f(wind_deg, 45))
        return [
            _f(anomaly), _f(wind_speed), np.sin(wind_rad), np.cos(wind_rad),
            _f(persistencia), float(hora), float(mes), _f(elite_score), _f(flujo), _f(perdida)
        ]

    def _build_dataset(self):
        if len(self.events) < MIN_EVENTS_FOR_ML: return np.array([]), np.array([]), np.array([]), []
        events_sorted = sorted(self.events, key=lambda e: e.get("fecha_deteccion", ""))
        X, y_class, y_reg, activos_list = [], [], [], []

        for i, event in enumerate(events_sorted):
            activo = event.get("activo_cercano", "")
            if not activo: continue
            X.append(self._extract_features(event))
            activos_list.append(activo)
            
            # Labeling
            try:
                fecha_base = datetime.fromisoformat(event.get("fecha_deteccion", "").replace("Z", "+00:00"))
                if fecha_base.tzinfo is None: fecha_base = fecha_base.replace(tzinfo=timezone.utc)
            except: fecha_base = datetime.now(timezone.utc)
            
            fecha_limite = fecha_base + timedelta(days=REINCIDENCE_DAYS)
            reincide, max_future_score = 0, 0.0
            for j in range(i + 1, len(events_sorted)):
                ev2 = events_sorted[j]
                if ev2.get("activo_cercano", "") != activo: continue
                try:
                    fecha2 = datetime.fromisoformat(ev2.get("fecha_deteccion", "").replace("Z", "+00:00"))
                    if fecha2.tzinfo is None: fecha2 = fecha2.replace(tzinfo=timezone.utc)
                except: continue
                if fecha2 > fecha_limite: break
                s2 = float(ev2.get("score_prioridad", ev2.get("elite_score", 0)) or 0)
                if s2 >= ELITE_THRESHOLD: reincide = 1
                max_future_score = max(max_future_score, s2)
            y_class.append(reincide)
            y_reg.append(max_future_score)

        return np.array(X), np.array(y_class), np.array(y_reg), activos_list

    def train(self):
        if not _SKLEARN_AVAILABLE: return {"status": "error", "method": "statistical"}
        X, y_class, y_reg, activos_list = self._build_dataset()
        if len(X) < MIN_EVENTS_FOR_ML: return {"status": "insufficient_data", "n": len(X)}

        X_scaled = self.scaler.fit_transform(X)
        self.rf_classifier = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight="balanced")
        self.rf_classifier.fit(X_scaled, y_class)
        self.gb_regressor = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
        self.gb_regressor.fit(X_scaled, y_reg)
        
        n_clusters = min(4, len(set(activos_list)))
        if n_clusters >= 2:
            self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            self.kmeans.fit(X_scaled)
        
        self._trained = True
        return {"status": "trained", "n_events": len(X), "method": "sklearn_rf"}

    def generate_ml_report(self, current_detections: List[Dict]) -> Dict:
        if not self._trained: self.train()
        results = []
        for det in current_detections:
            activo = det.get("activo_cercano", "")
            features = self._extract_features(det)
            X_scaled = self.scaler.transform([features])
            prob = float(self.rf_classifier.predict_proba(X_scaled)[0][1])
            f_score = float(self.gb_regressor.predict(X_scaled)[0])
            
            risk = "ALTO" if prob >= 0.7 else "MEDIO" if prob >= 0.4 else "BAJO"
            results.append({
                "activo": activo, "prob_reincidencia": round(prob, 4),
                "elite_score_futuro_estimado": round(f_score, 1),
                "nivel_riesgo": risk, "ch4_ppb_actual": det.get("intensidad_ppb", 0)
            })
        
        results.sort(key=lambda x: x["prob_reincidencia"], reverse=True)
        report = {
            "version": "3.7.1", "timestamp": datetime.now(timezone.utc).isoformat(),
            "resumen": { "total_analizados": len(results), "activo_mas_critico": results[0]["activo"] if results else None },
            "predicciones": results
        }
        return report

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyzer = MLPersistenceAnalyzer()
    print(f"Training: {analyzer.train()}")
    if analyzer.events:
        report = analyzer.generate_ml_report(analyzer.events[:10])
        print(json.dumps(report, indent=2))
