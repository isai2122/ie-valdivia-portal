import os
import json
import logging
from datetime import datetime, timezone

# Configuración básica
PROJECT_NAME = "MetanoSRGAN Elite v5.5"
BITACORA_PATH = "BITACORA_DESARROLLO_ACTUAL.md"

def generate_snapshot():
    print(f"🚀 Generando Snapshot de Estado: {PROJECT_NAME}")
    
    # 1. Verificar archivos clave
    files = ["backend/server.py", "frontend/app.js", "requirements.txt", ".env"]
    status_files = {f: os.path.exists(f) for f in files}
    
    # 2. Resumen de progreso (Bitácora)
    bitacora_content = "N/A"
    if os.path.exists(BITACORA_PATH):
        with open(BITACORA_PATH, 'r') as f:
            bitacora_content = f.read()

    # 3. Datos del sistema
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.5.0",
        "project": PROJECT_NAME,
        "files_verified": status_files,
        "last_log_entry": bitacora_content.split('\n')[-5:] if bitacora_content != "N/A" else "None",
        "instructions_for_successor": [
            "Conectarse a Google Drive y leer BITACORA_DESARROLLO_ACTUAL.md.",
            "Verificar la conexión a Supabase (debe haber ~450 detecciones).",
            "El frontend en /app debe mostrar el mapa con Heatmap y Plumas (mejorado v5.5).",
            "Continuar con la optimización de los modelos ML si es necesario."
        ]
    }
    
    snapshot_path = f"SNAPSHOT_ESTADO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snapshot_path, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"✓ Snapshot guardado en {snapshot_path}")
    return snapshot_path

if __name__ == "__main__":
    generate_snapshot()
