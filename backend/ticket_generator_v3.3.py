import json
import os
import uuid
from datetime import datetime

def generate_intervention_ticket(alert):
    """
    Genera un ticket de intervención en formato Markdown para una alerta específica.
    """
    ticket_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    ticket_content = f"""# 🎫 TICKET DE INTERVENCIÓN CRÍTICA: {ticket_id}
**Estado:** PENDIENTE DE ASIGNACIÓN  
**Prioridad:** ÉLITE (ALTA)  
**Fecha de Generación:** {timestamp}

---

## 1. Detalles de la Detección
- **Activo Afectado:** {alert['entidad']}
- **Coordenadas Fuente:** {alert['lat']}, {alert['lon']}
- **Concentración Detectada:** {round(alert['ppb'], 2)} ppb
- **Certificación Espectral:** {alert.get('certificacion_espectral', 'CERTIFICADO')} (MI: {alert.get('methane_index', 'N/A')})
- **Probabilidad de Gas Real:** {alert.get('probabilidad_gas_real', 0.98) * 100}%

## 2. Cuantificación de Impacto
- **Tasa de Emisión:** {alert.get('flujo_kgh', 0.0)} kg/h
- **Pérdida Económica:** ${alert.get('perdida_economica_usd_dia', 0.0)} USD/día
- **Impacto Ambiental:** {alert.get('impacto_co2e_anual_ton', 0.0)} Ton CO2e/año

## 3. Inteligencia de Campo (Proyección de Pluma)
- **Velocidad del Viento:** {alert.get('wind_speed', 0.0)} m/s
- **Dirección del Viento:** {alert.get('wind_deg', 0.0)}°
- **Alcance Proyectado (1h):** {alert.get('proyeccion_pluma', {}).get('distancia_alcance_km', 0.0)} km
- **Punto de Intercepción Sugerido:** {alert.get('proyeccion_pluma', {}).get('proyeccion_1h', [0,0])}

---

## 4. Instrucciones para el Equipo de Campo
1. **Verificación Visual:** Dirigirse a las coordenadas de la fuente con detector láser portátil.
2. **Seguridad:** Mantenerse a barlovento (viento a favor) durante la aproximación.
3. **Reporte:** Confirmar hallazgo y magnitud de la fuga mediante la App de Operaciones.

---
*Generado automáticamente por MetanoSRGAN Elite v3.3 - Sistema de Inteligencia Predictiva.*
"""
    
    filename = f"ticket_intervencion_{ticket_id}.md"
    with open(f"/home/ubuntu/{filename}", 'w') as f:
        f.write(ticket_content)
    
    return filename

if __name__ == "__main__":
    # Prueba
    sample_alert = {
        "entidad": "Vasconia",
        "lat": 5.918,
        "lon": -74.475,
        "ppb": 2500,
        "flujo_kgh": 0.25,
        "perdida_economica_usd_dia": 1.2,
        "wind_speed": 3.5,
        "wind_deg": 225,
        "proyeccion_pluma": {"distancia_alcance_km": 12.6, "proyeccion_1h": [5.99, -74.39]}
    }
    fname = generate_intervention_ticket(sample_alert)
    print(f"Ticket generado: {fname}")
