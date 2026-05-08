import json
import os
from high_res_api_bridge import HighResSatelliteBridge

def evaluate_tasking_roi(alert):
    """
    Evalúa si vale la pena solicitar una imagen de alta resolución (Tasking)
    basándose en el Elite Score y la pérdida económica detectada.
    """
    elite_score = alert.get('elite_score', 0)
    perdida_usd_dia = alert.get('perdida_economica_usd_dia', 0)
    
    # Umbrales de decisión
    # 1. Si el Elite Score es > 100 (Crítico absoluto)
    # 2. Si la pérdida económica es > $50 USD/día (El costo de la imagen se recupera en 10 días)
    
    should_task = False
    reason = ""
    
    if elite_score >= 100:
        should_task = True
        reason = f"Elite Score Crítico ({elite_score})"
    elif perdida_usd_dia >= 50:
        should_task = True
        reason = f"Alto Impacto Económico (${perdida_usd_dia} USD/día)"
        
    return should_task, reason

def process_alerts_for_tasking(alerts):
    """
    Procesa una lista de alertas y solicita tasking para las que califiquen.
    """
    bridge = HighResSatelliteBridge()
    tasking_requests = []
    
    for alert in alerts:
        should_task, reason = evaluate_tasking_roi(alert)
        
        if should_task:
            lat, lon = alert['coordenadas_fuga']
            task_res = bridge.request_tasking(lat, lon)
            
            task_info = {
                "alert_id": alert.get('id', 'N/A'),
                "reason": reason,
                "tasking_status": task_res['status'],
                "request_id": task_res['request_id'],
                "estimated_capture": task_res['estimated_capture'],
                "cost_usd": task_res['cost_estimate_usd']
            }
            tasking_requests.append(task_info)
            alert['tasking_requested'] = True
            alert['tasking_info'] = task_info
            
    return alerts, tasking_requests

if __name__ == "__main__":
    # Prueba con una alerta crítica
    test_alert = {
        "id": "AL-001",
        "coordenadas_fuga": [7.065, -73.854],
        "elite_score": 105,
        "perdida_economica_usd_dia": 65.0
    }
    
    alerts, tasks = process_alerts_for_tasking([test_alert])
    print(f"Alertas procesadas: {json.dumps(alerts, indent=2)}")
    print(f"Solicitudes de Tasking: {json.dumps(tasks, indent=2)}")
