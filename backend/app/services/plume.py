"""Generador de polígonos (elipses) para representar plumas."""
import math
from typing import Any, Dict

from shapely.affinity import rotate, scale, translate
from shapely.geometry import Point, mapping


def make_plume_polygon(
    lat: float,
    lng: float,
    area_km2: float,
    wind_dir_deg: float,
    vertices: int = 12,
) -> Dict[str, Any]:
    """Genera un GeoJSON Polygon elíptico, alargado en la dirección del viento.

    `wind_dir_deg` sigue la convención meteorológica: desde dónde sopla el viento
    (0 = Norte, 90 = Este). El penacho se elonga en la dirección hacia donde
    se desplaza.
    """
    vertices = max(4, min(16, vertices))
    # semi-ejes: ratio 3:1 (plume alargada)
    a_km = math.sqrt(area_km2 / math.pi) * 1.8  # semi-major (km)
    b_km = area_km2 / (math.pi * max(a_km, 1e-3))  # semi-minor (km)

    deg_per_km_lat = 1.0 / 111.0
    deg_per_km_lng = 1.0 / (111.0 * max(math.cos(math.radians(lat)), 0.2))

    # Círculo unidad -> elipse (en grados lng/lat aprox).
    # Shapely.Point.buffer(1, resolution=r) -> 4*r vértices.
    res = max(1, vertices // 4)
    base = Point(0, 0).buffer(1.0, resolution=res)
    ell = scale(base, a_km * deg_per_km_lng, b_km * deg_per_km_lat, origin=(0, 0))

    # Dirección de transporte (hacia donde va el viento) en convención matemática.
    transport_math_deg = (90.0 - (wind_dir_deg + 180.0)) % 360.0
    ell = rotate(ell, transport_math_deg, origin=(0, 0), use_radians=False)

    # Desplazar el centroide río abajo desde el punto de origen.
    offset_km = a_km * 0.6
    dx = offset_km * math.cos(math.radians(transport_math_deg)) * deg_per_km_lng
    dy = offset_km * math.sin(math.radians(transport_math_deg)) * deg_per_km_lat
    ell = translate(ell, lng + dx, lat + dy)

    return mapping(ell)
