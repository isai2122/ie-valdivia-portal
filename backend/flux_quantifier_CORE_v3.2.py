import numpy as np
import json
import os

def calculate_flux_ime(ppb_enhancement, wind_speed_ms, resolution_m=10):
    """
    Calcula la tasa de emisión (Q) en kg/h usando una versión simplificada del 
    método Integrated Mass Enhancement (IME).
    
    Q = (IME * U_eff) / L
    Donde:
    - IME: Masa total de metano en exceso en la pluma (kg).
    - U_eff: Velocidad efectiva del viento (m/s).
    - L: Longitud característica de la pluma (m).
    """
    # 1. Convertir ppb de exceso a densidad de columna (kg/m2)
    # Factor de conversión aproximado: 1 ppb ~ 1.24e-8 kg/m2 (depende de la presión/temperatura)
    # Para Sentinel-2 (columna total), usamos un factor de sensibilidad de columna.
    # Un valor típico de realce de columna para metano es ~5.3e-9 kg/m2 por ppb.
    k_conv = 5.3e-9 
    
    # Masa en exceso por píxel (kg)
    pixel_area = resolution_m ** 2
    mass_per_pixel = ppb_enhancement * k_conv * pixel_area
    
    # 2. Velocidad efectiva del viento (U_eff)
    # La velocidad efectiva suele ser una fracción de la velocidad a 10m (U10)
    # U_eff = alpha * U10. Un valor común es alpha = 0.6
    u_eff = 0.6 * wind_speed_ms
    
    # 3. Longitud característica (L)
    # Para un píxel de 10m, L es aproximadamente la raíz del área del píxel.
    l_char = resolution_m
    
    # 4. Tasa de emisión (kg/s)
    q_kgs = (mass_per_pixel * u_eff) / l_char
    
    # Convertir a kg/h
    q_kgh = q_kgs * 3600
    
    return round(float(q_kgh), 2)

def quantify_detections(certified_detections, wind_data=None):
    """
    Aplica la cuantificación a una lista de detecciones certificadas.
    """
    quantified_results = []
    
    # Precio del gas natural (aproximado: $4.00 USD por MMBtu -> ~$0.20 USD por kg de CH4)
    # Nota: El precio varía, pero usamos un valor conservador para la industria.
    GAS_PRICE_PER_KG = 0.20 
    
    for det in certified_detections:
        # Obtener velocidad del viento (si no hay, usamos un promedio de 2.5 m/s para el Magdalena Medio)
        u10 = det.get('wind_speed', 2.5)
        
        # Realce de ppb (ppb detectado - fondo de ~1900 ppb)
        ppb_excess = max(0, det['ppb'] - 1900)
        
        # Calcular flujo
        flux_kgh = calculate_flux_ime(ppb_excess, u10)
        
        # Valoración económica (USD/día si la fuga persiste)
        loss_usd_day = flux_kgh * 24 * GAS_PRICE_PER_KG
        
        det['flujo_kgh'] = flux_kgh
        det['perdida_economica_usd_dia'] = round(loss_usd_day, 2)
        det['impacto_co2e_anual_ton'] = round((flux_kgh * 24 * 365 * 28) / 1000, 2) # GWP CH4 = 28
        
        quantified_results.append(det)
        
    return quantified_results

if __name__ == "__main__":
    # Prueba
    sample_det = [
        {"lat": 5.918, "lon": -74.475, "ppb": 2500, "wind_speed": 3.2}
    ]
    res = quantify_detections(sample_det)
    print(json.dumps(res, indent=2))
