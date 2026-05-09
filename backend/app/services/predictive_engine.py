"""
Motor de Análisis de Recurrencia Real - MetanoSRGAN Elite v5.2
Analiza la frecuencia y severidad histórica de los 409 eventos reales de Sentinel-5P.
SIN DATOS SIMULADOS.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

class PredictiveEngine:
    def __init__(self, data_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json"):
        self.data_path = Path(data_path)
        self.events = self._load_data()
        
    def _load_data(self) -> List[Dict]:
        try:
            # Usamos la ruta absoluta correcta
            target_path = Path("/home/ubuntu/metanosrgan_v50/backend/data/events_real.json")
            if not target_path.exists():
                return []
            with open(target_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def analyze_real_recurrence(self) -> Dict[str, Any]:
        """Analiza la recurrencia histórica real por estación"""
        if not self.events:
            return {"status": "error", "message": "No hay datos reales cargados"}

        # 1. Frecuencia Real por Estación
        # En los datos reales la llave es 'activo_cercano'
        stations = [e.get('activo_cercano', 'Desconocido') for e in self.events]
        station_counts = Counter(stations)
        
        # 2. Análisis de Severidad Real
        severity_by_station = {}
        for e in self.events:
            station = e.get('activo_cercano', 'Desconocido')
            if station not in severity_by_station:
                severity_by_station[station] = []
            severity_by_station[station].append(e.get('intensidad_ppb', 0))

        # 3. Cálculo de Ranking de Riesgo basado en DATOS HISTÓRICOS REALES
        total_events = len(self.events)
        risk_ranking = []
        for station, count in station_counts.items():
            ppbs = severity_by_station[station]
            avg_ppb = sum(ppbs) / len(ppbs) if ppbs else 0
            max_ppb = max(ppbs) if ppbs else 0
            
            # El riesgo es una medida de recurrencia histórica real
            recurrence_rate = (count / total_events) * 100
            
            risk_ranking.append({
                "station": station,
                "event_count": count,
                "recurrence_rate": round(recurrence_rate, 2),
                "avg_ppb": round(avg_ppb, 2),
                "max_ppb": round(max_ppb, 2),
                "risk_level": "Crítico" if recurrence_rate > 20 else "Alto" if recurrence_rate > 10 else "Moderado"
            })

        return {
            "analysis_date": datetime.now().isoformat(),
            "total_real_events": total_events,
            "station_recurrence_ranking": sorted(risk_ranking, key=lambda x: x['event_count'], reverse=True),
            "data_source": "Sentinel-5P TROPOMI - Magdalena Medio"
        }
