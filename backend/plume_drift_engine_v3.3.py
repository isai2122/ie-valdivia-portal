import numpy as np
import math
import json

def project_plume(lat, lon, wind_speed_ms, wind_deg, duration_h=1.0):
    """
    Proyecta la trayectoria de la pluma de metano basándose en el viento.
    - lat, lon: Coordenadas de la fuente.
    - wind_speed_ms: Velocidad del viento en m/s.
    - wind_deg: Dirección del viento en grados (0=N, 90=E, 180=S, 270=W).
    - duration_h: Tiempo de proyección en horas.
    """
    # 1. Convertir dirección del viento a radianes (matemáticos, 0=E, 90=N)
    # En meteorología, 0 es Norte y va en sentido horario.
    # Para cálculos, necesitamos el ángulo hacia donde VA el viento.
    angle_rad = math.radians((270 - wind_deg) % 360)
    
    # 2. Distancia recorrida en km
    distance_km = (wind_speed_ms * 3.6) * duration_h
    
    # 3. Calcular nuevas coordenadas (aproximación Haversine inversa simplificada)
    # 1 grado latitud ~ 111 km
    # 1 grado longitud ~ 111 * cos(lat) km
    delta_lat = (distance_km * math.sin(angle_rad)) / 111.0
    delta_lon = (distance_km * math.cos(angle_rad)) / (111.0 * math.cos(math.radians(lat)))
    
    target_lat = lat + delta_lat
    target_lon = lon + delta_lon
    
    return {
        "origen": [lat, lon],
        "proyeccion_1h": [target_lat, target_lon],
        "distancia_alcance_km": round(distance_km, 2),
        "direccion_viento_deg": wind_deg,
        "velocidad_viento_ms": wind_speed_ms
    }

def add_drift_to_alerts(alerts):
    """
    Añade la proyección de pluma a cada alerta detectada.
    """
    for alert in alerts:
        # Si no hay dirección de viento, simulamos una predominante en el Magdalena Medio (Noreste ~45°)
        wind_deg = alert.get('wind_deg', 45.0)
        wind_speed = alert.get('wind_speed', 2.5)
        
        drift = project_plume(alert['lat'], alert['lon'], wind_speed, wind_deg)
        alert['proyeccion_pluma'] = drift
        
    return alerts

if __name__ == "__main__":
    # Prueba
    test_lat, test_lon = 5.918, -74.475
    res = project_plume(test_lat, test_lon, 3.5, 225) # Viento del Suroeste (va hacia el Noreste)
    print(json.dumps(res, indent=2))
