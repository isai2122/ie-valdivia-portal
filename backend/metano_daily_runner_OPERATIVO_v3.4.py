import os
import json
import datetime
from full_validation import run_full_validation
from plume_drift_engine import add_drift_to_alerts
from ticket_generator import generate_intervention_ticket
from auto_tasking_logic import process_alerts_for_tasking
from visual_comparison_engine import generate_visual_validation_report

def main():
    print(f"--- INICIANDO EJECUCIÓN DIARIA: METANOSRGAN ELITE v3.4 ---")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Ejecutar el pipeline completo de validación, certificación y cuantificación
    try:
        run_full_validation()
        print("\n[OK] Pipeline base ejecutado con éxito.")
    except Exception as e:
        print(f"\n[ERROR] Fallo en la ejecución del pipeline: {e}")
        return

    # 2. Cargar resultados para inteligencia predictiva y validación visual
    if os.path.exists('reporte_validacion_completa.json'):
        with open('reporte_validacion_completa.json', 'r') as f:
            results = json.load(f)
        
        print("\n--- PROCESANDO INTELIGENCIA PREDICTIVA Y VALIDACIÓN VISUAL v3.4 ---")
        total_tickets = 0
        total_tasking = 0
        
        for station_res in results:
            # Añadir proyección de plumas a las alertas
            station_res['detalle_alertas'] = add_drift_to_alerts(station_res['detalle_alertas'])
            
            # Procesar Tasking Automático (Alta Resolución)
            station_res['detalle_alertas'], tasking_reqs = process_alerts_for_tasking(station_res['detalle_alertas'])
            total_tasking += len(tasking_reqs)
            
            # Generar reportes de validación visual para las que tienen tasking
            for alert in station_res['detalle_alertas']:
                if alert.get('tasking_requested'):
                    generate_visual_validation_report(alert, alert['tasking_info'])
            
            # Generar tickets para alertas críticas
            for alert in station_res['detalle_alertas']:
                if alert.get('elite_score', 0) > 80:
                    generate_intervention_ticket(alert)
                    total_tickets += 1
        
        # Guardar reporte enriquecido v3.4
        with open('reporte_operativo_ENRIQUECIDO_v3.4.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        total_alertas = sum(r['alertas_encontradas'] for r in results)
        total_perdida = sum(sum(a['perdida_economica_usd_dia'] for a in r['detalle_alertas']) for r in results)
        
        print(f"\n--- RESUMEN OPERATIVO v3.4 ---")
        print(f"Total Alertas Certificadas: {total_alertas}")
        print(f"Tickets de Intervención Generados: {total_tickets}")
        print(f"Solicitudes de Alta Resolución (Tasking): {total_tasking}")
        print(f"Pérdida Económica Total Detectada: ${round(total_perdida, 2)} USD/día")
        print(f"------------------------------")
        
        if total_tasking > 0:
            print("Validación Visual de Alta Resolución en curso para alertas críticas.")

    print(f"\n--- EJECUCIÓN v3.4 FINALIZADA ---")

if __name__ == "__main__":
    main()
