"""
Motor de Detección de Anomalías Estadísticas - MetanoSRGAN Elite v5.3
Utiliza Z-Score para identificar eventos atípicos en los 409 datos reales.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import statistics

class AnomalyDetector:
    def __init__(self, data_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json", z_threshold: float = 2.0):
        self.data_path = Path(data_path)
        self.events = self._load_data()
        self.z_threshold = z_threshold  # Umbral de Z-Score (2.0 = 95% confianza)
        
    def _load_data(self) -> List[Dict]:
        try:
            if not self.data_path.exists():
                return []
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def detect_anomalies_by_station(self) -> Dict[str, Any]:
        """Detecta anomalías por estación usando Z-Score"""
        if not self.events:
            return {"status": "error", "message": "No hay datos"}

        # Agrupar eventos por estación
        by_station = {}
        for e in self.events:
            station = e.get('activo_cercano', 'Desconocido')
            if station not in by_station:
                by_station[station] = []
            by_station[station].append(e)

        anomalies = []
        for station, events in by_station.items():
            ppbs = [e.get('intensidad_ppb', 0) for e in events]
            
            if len(ppbs) < 2:
                continue
                
            mean = statistics.mean(ppbs)
            stdev = statistics.stdev(ppbs) if len(ppbs) > 1 else 0
            
            if stdev == 0:
                continue
            
            # Calcular Z-Score para cada evento
            for e in events:
                ppb = e.get('intensidad_ppb', 0)
                z_score = (ppb - mean) / stdev
                
                if abs(z_score) > self.z_threshold:
                    anomalies.append({
                        "id": e.get('id_evento', 'N/A'),
                        "station": station,
                        "ppb": ppb,
                        "z_score": round(z_score, 2),
                        "mean_station": round(mean, 2),
                        "severity": "Extremo" if abs(z_score) > 3.0 else "Alto",
                        "date": e.get('fecha_deteccion', 'N/A')
                    })

        return {
            "total_anomalies": len(anomalies),
            "anomalies": sorted(anomalies, key=lambda x: abs(x['z_score']), reverse=True),
            "z_threshold": self.z_threshold
        }

    def get_infrastructure_impact(self) -> Dict[str, Any]:
        """Analiza el impacto potencial en infraestructura crítica (radio 5km)"""
        if not self.events:
            return {}

        # Definir infraestructuras críticas (coordenadas aproximadas)
        critical_infrastructure = {
            "Vasconia": {"lat": 6.0167, "lng": -74.4833, "type": "Estación de Compresión"},
            "Mariquita": {"lat": 5.2000, "lng": -74.9000, "type": "Estación de Compresión"},
            "Barrancabermeja": {"lat": 7.0647, "lng": -73.8542, "type": "Refinería"},
            "Malena": {"lat": 5.8500, "lng": -74.1000, "type": "Estación de Compresión"},
            "Miraflores": {"lat": 5.2069, "lng": -73.1500, "type": "Estación de Compresión"},
        }

        impact_analysis = {}
        for infra_name, infra_data in critical_infrastructure.items():
            # Contar eventos dentro de 5km
            nearby_events = []
            for e in self.events:
                if 'latitud' in e and 'longitud' in e:
                    # Cálculo simple de distancia (aproximado)
                    lat_diff = abs(e['latitud'] - infra_data['lat']) * 111  # ~111km por grado
                    lng_diff = abs(e['longitud'] - infra_data['lng']) * 111 * 0.7  # Ajuste por latitud
                    distance = (lat_diff**2 + lng_diff**2)**0.5
                    
                    if distance < 5:
                        nearby_events.append({
                            "distance_km": round(distance, 2),
                            "ppb": e.get('intensidad_ppb', 0),
                            "date": e.get('fecha_deteccion', 'N/A')
                        })
            
            if nearby_events:
                impact_analysis[infra_name] = {
                    "type": infra_data['type'],
                    "nearby_events_count": len(nearby_events),
                    "avg_ppb_nearby": round(sum(e['ppb'] for e in nearby_events) / len(nearby_events), 2),
                    "risk_level": "Crítico" if len(nearby_events) > 20 else "Alto" if len(nearby_events) > 10 else "Moderado"
                }

        return impact_analysis
