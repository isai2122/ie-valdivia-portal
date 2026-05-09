"""
Exportador GIS Real - MetanoSRGAN Elite v5.2
Convierte los 409 eventos reales a GeoJSON/KML.
"""

import json
from pathlib import Path
from typing import List, Dict

class GISExporter:
    def __init__(self, events_path: str = "/home/ubuntu/metanosrgan_v50/backend/data/events_real.json"):
        self.events_path = Path(events_path)
        
    def _load_events(self) -> List[Dict]:
        try:
            if not self.events_path.exists():
                return []
            with open(self.events_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def to_geojson(self) -> Dict:
        """Genera GeoJSON con los 409 puntos reales"""
        events = self._load_events()
        features = []
        for e in events:
            # Usar llaves reales: latitud, longitud, intensidad_ppb
            if 'latitud' in e and 'longitud' in e:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [e['longitud'], e['latitud']]
                    },
                    "properties": {
                        "id": e.get('id_deteccion', 'N/A'),
                        "station": e.get('activo_cercano', 'N/A'),
                        "ppb": e.get('intensidad_ppb', 0),
                        "date": e.get('fecha_deteccion', 'N/A'),
                        "category": e.get('categoria_alerta', 'N/A')
                    }
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def to_kml(self) -> str:
        """Genera KML real para Google Earth"""
        events = self._load_events()
        kml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            '<Document>',
            '  <name>MetanoSRGAN Real Events</name>'
        ]

        for e in events:
            if 'latitud' in e and 'longitud' in e:
                kml.append('  <Placemark>')
                kml.append(f'    <name>{e.get("activo_cercano", "Evento")} - {e.get("intensidad_ppb", 0)} ppb</name>')
                kml.append(f'    <Point><coordinates>{e["longitud"]},{e["latitud"]},0</coordinates></Point>')
                kml.append('  </Placemark>')

        kml.extend(['</Document>', '</kml>'])
        return "\n".join(kml)
