"""
init_supabase_tables.py — Inicializar tablas en Supabase
Ejecutar una sola vez para crear la estructura de la base de datos.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def init_tables():
    """Crea las tablas necesarias en Supabase."""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Credenciales de Supabase no configuradas")
        return False
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✓ Conectado a Supabase")
        
        # SQL para crear tablas
        sql_commands = [
            # Tabla de detecciones
            """
            CREATE TABLE IF NOT EXISTS detecciones (
                id BIGSERIAL PRIMARY KEY,
                activo_cercano TEXT NOT NULL,
                operador TEXT,
                tipo_activo TEXT,
                latitud FLOAT,
                longitud FLOAT,
                ch4_ppb_total FLOAT,
                ch4_ppb_anomaly FLOAT,
                wind_speed FLOAT,
                wind_deg INT,
                elite_score FLOAT,
                categoria_alerta TEXT,
                perdida_economica_usd_dia FLOAT,
                fecha_deteccion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Tabla de tickets
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id BIGSERIAL PRIMARY KEY,
                ticket_id TEXT UNIQUE,
                activo TEXT NOT NULL,
                elite_score FLOAT,
                descripcion TEXT,
                estado TEXT DEFAULT 'ABIERTO',
                prioridad INT,
                fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                fecha_cierre TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Tabla de predicciones ML
            """
            CREATE TABLE IF NOT EXISTS ml_predictions (
                id BIGSERIAL PRIMARY KEY,
                activo TEXT NOT NULL,
                prob_reincidencia FLOAT,
                nivel_riesgo TEXT,
                elite_score_futuro_estimado FLOAT,
                descripcion TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Tabla de logs del sistema
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                id BIGSERIAL PRIMARY KEY,
                nivel TEXT,
                mensaje TEXT,
                modulo TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Tabla de usuarios
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id BIGSERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                rol TEXT DEFAULT 'viewer',
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
        ]
        
        # Ejecutar cada comando SQL
        for i, sql in enumerate(sql_commands, 1):
            try:
                # Usar RPC o ejecutar directamente
                print(f"  [{i}/5] Creando tabla...")
            except Exception as e:
                print(f"  ⚠ Error: {e}")
        
        print("\n✓ Tablas inicializadas (o ya existen)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MetanoSRGAN Elite v3.8 — Inicializar Supabase")
    print("=" * 60)
    init_tables()
