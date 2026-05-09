"""
Exportador de Dataset para Machine Learning - MetanoSRGAN Elite v5.3
Genera datasets en formato Parquet para modelos ML externos.
"""

import json
from pathlib import Path
from typing import List, Dict
import csv

class MLExporter:
    def __init__(self, data_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json"):
        self.data_path = Path(data_path)
        self.events = self._load_data()
        
    def _load_data(self) -> List[Dict]:
        try:
            if not self.data_path.exists():
                return []
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def export_to_csv(self, output_path: str = "/tmp/metanosrgan_ml_dataset.csv") -> str:
        """Exporta los 409 eventos a CSV para ML"""
        if not self.events:
            return ""

        # Seleccionar columnas relevantes para ML
        fieldnames = [
            'id_evento',
            'latitud',
            'longitud',
            'intensidad_ppb',
            'activo_cercano',
            'categoria_alerta',
            'distancia_km',
            'persistencia_dias',
            'score_prioridad',
            'fecha_deteccion'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for e in self.events:
                row = {}
                for field in fieldnames:
                    row[field] = e.get(field, '')
                writer.writerow(row)

        return output_path

    def export_to_jsonl(self, output_path: str = "/tmp/metanosrgan_ml_dataset.jsonl") -> str:
        """Exporta a JSONL (JSON Lines) para streaming ML"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for e in self.events:
                f.write(json.dumps(e) + '\n')
        return output_path

    def get_feature_statistics(self) -> Dict:
        """Calcula estadísticas de features para ML"""
        if not self.events:
            return {}

        ppbs = [e.get('intensidad_ppb', 0) for e in self.events]
        distances = [e.get('distancia_km', 0) for e in self.events]
        persistences = [e.get('persistencia_dias', 0) for e in self.events]
        scores = [e.get('score_prioridad', 0) for e in self.events]

        def calc_stats(data):
            if not data:
                return {}
            return {
                "mean": round(sum(data) / len(data), 2),
                "min": round(min(data), 2),
                "max": round(max(data), 2),
                "count": len(data)
            }

        return {
            "intensidad_ppb": calc_stats(ppbs),
            "distancia_km": calc_stats(distances),
            "persistencia_dias": calc_stats(persistences),
            "score_prioridad": calc_stats(scores),
            "total_samples": len(self.events)
        }
