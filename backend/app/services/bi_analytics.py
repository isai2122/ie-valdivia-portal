"""
Módulo de Inteligencia de Negocios (BI) - MetanoSRGAN Elite v5.3
Análisis comparativo de operadoras y eficiencia operacional.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

class BIAnalytics:
    def __init__(self, data_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json"):
        self.data_path = Path(data_path)
        self.events = self._load_data()
        
        # Mapeo de estaciones a operadoras
        self.station_to_operator = {
            "Vasconia": "Cenit Transporte",
            "Mariquita": "Cenit Transporte",
            "Barrancabermeja": "Ecopetrol",
            "Malena": "Cenit Transporte",
            "Miraflores": "Cenit Transporte",
        }
        
    def _load_data(self) -> List[Dict]:
        try:
            if not self.data_path.exists():
                return []
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def compare_operators(self) -> Dict[str, Any]:
        """Compara eficiencia y desempeño entre operadoras"""
        if not self.events:
            return {}

        # Agrupar por operadora
        by_operator = {}
        for e in self.events:
            station = e.get('activo_cercano', 'Desconocido')
            operator = self.station_to_operator.get(station, 'Desconocida')
            
            if operator not in by_operator:
                by_operator[operator] = {
                    "events": [],
                    "stations": set()
                }
            
            by_operator[operator]["events"].append(e)
            by_operator[operator]["stations"].add(station)

        # Calcular métricas por operadora
        comparison = {}
        for operator, data in by_operator.items():
            events = data["events"]
            ppbs = [e.get('intensidad_ppb', 0) for e in events]
            
            # Categorías de alerta
            critical = sum(1 for e in events if "CRÍTICA" in e.get('categoria_alerta', ''))
            preventive = sum(1 for e in events if "PREVENTIVA" in e.get('categoria_alerta', ''))
            
            comparison[operator] = {
                "total_events": len(events),
                "stations_managed": len(data["stations"]),
                "avg_ppb": round(sum(ppbs) / len(ppbs), 2) if ppbs else 0,
                "max_ppb": round(max(ppbs), 2) if ppbs else 0,
                "min_ppb": round(min(ppbs), 2) if ppbs else 0,
                "critical_alerts": critical,
                "preventive_alerts": preventive,
                "efficiency_score": round(100 - (critical / len(events) * 100), 2) if events else 0
            }

        return comparison

    def get_station_performance(self) -> List[Dict]:
        """Ranking de desempeño por estación"""
        if not self.events:
            return []

        by_station = {}
        for e in self.events:
            station = e.get('activo_cercano', 'Desconocido')
            if station not in by_station:
                by_station[station] = {
                    "events": [],
                    "operator": self.station_to_operator.get(station, 'Desconocida')
                }
            by_station[station]["events"].append(e)

        performance = []
        for station, data in by_station.items():
            events = data["events"]
            ppbs = [e.get('intensidad_ppb', 0) for e in events]
            critical = sum(1 for e in events if "CRÍTICA" in e.get('categoria_alerta', ''))
            
            performance.append({
                "station": station,
                "operator": data["operator"],
                "event_count": len(events),
                "avg_ppb": round(sum(ppbs) / len(ppbs), 2) if ppbs else 0,
                "critical_count": critical,
                "risk_score": round((critical / len(events) * 100) if events else 0, 2)
            })

        return sorted(performance, key=lambda x: x['risk_score'], reverse=True)
