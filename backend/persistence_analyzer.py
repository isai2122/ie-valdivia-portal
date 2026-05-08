import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)

class PersistenceAnalyzer:
    """Analiza la persistencia de detecciones y calcula scores de prioridad"""
    
    def __init__(self, master_table_path: str):
        self.master_table_path = master_table_path
        self.events = self._load_events()

    def _load_events(self) -> List[Dict]:
        try:
            with open(self.master_table_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando tabla maestra: {e}")
            return []

    def analyze_persistence(self, radius_km: float = 2.0) -> List[Dict]:
        """
        Calcula cuántos días seguidos se ha detectado metano en la misma zona
        """
        if not self.events:
            return []

        # Ordenar por fecha descendente
        sorted_events = sorted(self.events, key=lambda x: x['fecha_deteccion'], reverse=True)
        
        for i, event in enumerate(sorted_events):
            if 'persistencia_dias' not in event or event['persistencia_dias'] <= 1:
                count = 1
                event_date = datetime.fromisoformat(event['fecha_deteccion']).date()
                
                # Buscar detecciones previas en el mismo radio
                for prev_event in sorted_events[i+1:]:
                    prev_date = datetime.fromisoformat(prev_event['fecha_deteccion']).date()
                    
                    # Si es el mismo día, ignorar (ya contado o es la misma pasada)
                    if prev_date == event_date:
                        continue
                    
                    # Si es un día anterior
                    if prev_date < event_date:
                        # Calcular distancia
                        dist = self._haversine(
                            event['latitud'], event['longitud'],
                            prev_event['latitud'], prev_event['longitud']
                        )
                        
                        if dist <= radius_km:
                            count += 1
                            event_date = prev_date # Buscar el día anterior a este
                        else:
                            # Si no hay en este día anterior, la cadena se rompe
                            if (event_date - prev_date).days > 1:
                                break
                
                event['persistencia_dias'] = count
        
        return sorted_events

    def calculate_priority_scores(self) -> List[Dict]:
        """
        Calcula un score de 0-100 basado en:
        - Intensidad (40%)
        - Persistencia (30%)
        - Proximidad a activos (30%)
        """
        for event in self.events:
            # Normalizar Intensidad (asumiendo max 3000 ppb)
            intensity_score = min(event['intensidad_ppb'] / 3000 * 100, 100)
            
            # Persistencia (max 10 días para score full)
            persistence = event.get('persistencia_dias', 1)
            persistence_score = min(persistence / 10 * 100, 100)
            
            # Proximidad (0km = 100, >5km = 0)
            distance = event.get('distancia_km', 5)
            proximity_score = max((5 - distance) / 5 * 100, 0)
            
            # Score Final
            final_score = (intensity_score * 0.4) + (persistence_score * 0.3) + (proximity_score * 0.3)
            event['score_prioridad'] = round(final_score, 2)
            
            # Actualizar categoría basada en score
            if final_score > 70:
                event['categoria_alerta'] = "ALERTA CRÍTICA"
            elif final_score > 40:
                event['categoria_alerta'] = "ALERTA PREVENTIVA"
            else:
                event['categoria_alerta'] = "MONITOREO RUTINARIO"
                
        return self.events

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371 # Radio de la Tierra en km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c

    def save_results(self):
        try:
            with open(self.master_table_path, 'w') as f:
                json.dump(self.events, f, indent=2)
            logger.info(f"Resultados guardados en {self.master_table_path}")
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

if __name__ == "__main__":
    analyzer = PersistenceAnalyzer("/home/ubuntu/event_master_table.json")
    analyzer.analyze_persistence()
    analyzer.calculate_priority_scores()
    analyzer.save_results()
    print("Análisis de persistencia y prioridad completado.")
