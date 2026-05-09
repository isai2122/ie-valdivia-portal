"""
Módulo de Auditoría de Integridad de Datos - MetanoSRGAN Elite v5.3
Valida la integridad y calidad de los 409 eventos reales.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class DataAuditor:
    def __init__(self, data_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json"):
        self.data_path = Path(data_path)
        self.events = self._load_data()
        self.audit_report = {}
        
    def _load_data(self) -> List[Dict]:
        try:
            if not self.data_path.exists():
                return []
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def audit_data_integrity(self) -> Dict[str, Any]:
        """Realiza auditoría completa de integridad de datos"""
        if not self.events:
            return {"status": "error", "message": "No hay datos para auditar"}

        audit = {
            "total_records": len(self.events),
            "checks": {}
        }

        # 1. Verificar campos obligatorios
        missing_fields = {
            "id_evento": 0,
            "latitud": 0,
            "longitud": 0,
            "intensidad_ppb": 0,
            "activo_cercano": 0,
            "fecha_deteccion": 0
        }

        for e in self.events:
            for field in missing_fields.keys():
                if field not in e or e[field] is None:
                    missing_fields[field] += 1

        audit["checks"]["missing_fields"] = missing_fields

        # 2. Detectar duplicados
        ids = [e.get('id_evento') for e in self.events]
        duplicates = len(ids) - len(set(ids))
        audit["checks"]["duplicate_ids"] = duplicates

        # 3. Validar rangos de coordenadas (Magdalena Medio)
        valid_coords = 0
        invalid_coords = 0
        for e in self.events:
            lat = e.get('latitud', 0)
            lng = e.get('longitud', 0)
            # Magdalena Medio: ~5-7°N, ~73-75°W
            if 4.5 <= lat <= 7.5 and -75 <= lng <= -72.5:
                valid_coords += 1
            else:
                invalid_coords += 1

        audit["checks"]["coordinate_validation"] = {
            "valid": valid_coords,
            "invalid": invalid_coords
        }

        # 4. Validar rangos de PPB
        ppb_stats = {
            "below_2000": 0,
            "2000_2100": 0,
            "2100_2200": 0,
            "2200_2300": 0,
            "above_2300": 0
        }

        for e in self.events:
            ppb = e.get('intensidad_ppb', 0)
            if ppb < 2000:
                ppb_stats["below_2000"] += 1
            elif ppb < 2100:
                ppb_stats["2000_2100"] += 1
            elif ppb < 2200:
                ppb_stats["2100_2200"] += 1
            elif ppb < 2300:
                ppb_stats["2200_2300"] += 1
            else:
                ppb_stats["above_2300"] += 1

        audit["checks"]["ppb_distribution"] = ppb_stats

        # 5. Validar fechas
        invalid_dates = 0
        for e in self.events:
            try:
                datetime.fromisoformat(e.get('fecha_deteccion', '').replace('Z', ''))
            except Exception:
                invalid_dates += 1

        audit["checks"]["invalid_dates"] = invalid_dates

        # 6. Resumen de estaciones
        stations = {}
        for e in self.events:
            station = e.get('activo_cercano', 'Desconocida')
            stations[station] = stations.get(station, 0) + 1

        audit["checks"]["station_distribution"] = stations

        # 7. Calidad general
        total_issues = (
            sum(missing_fields.values()) +
            duplicates +
            invalid_coords +
            invalid_dates
        )

        data_quality = round(100 - (total_issues / (len(self.events) * 6) * 100), 2)
        audit["data_quality_score"] = data_quality
        audit["status"] = "PASS" if data_quality > 95 else "WARNING" if data_quality > 90 else "FAIL"

        return audit
