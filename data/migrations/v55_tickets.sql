-- =====================================================================
-- MetanoSRGAN Elite v5.5 — Migración tabla `tickets` a schema v5.5
-- =====================================================================
-- EJECUTAR EN: Supabase Dashboard → SQL Editor → New query → Run
--
-- ⚠ ATENCIÓN: este script ELIMINA y RECREA la tabla `tickets`.
-- Si ya tienes tickets viejos en producción, primero exporta:
--    SELECT * FROM tickets;  -- copia el resultado a CSV antes
--
-- Si la tabla `tickets` está vacía o solo tiene datos de prueba,
-- ejecuta directamente. Después del CREATE, los nuevos tickets que
-- genere el pipeline se persistirán correctamente en Supabase
-- (ya no solo en JSON local).
-- =====================================================================

-- 1. Backup opcional de tickets antiguos (descomentar si necesitas):
-- CREATE TABLE tickets_v54_backup AS SELECT * FROM tickets;

-- 2. Drop tabla legacy
DROP TABLE IF EXISTS tickets CASCADE;

-- 3. Crear tabla v5.5
CREATE TABLE tickets (
    id                    BIGSERIAL PRIMARY KEY,
    ticket_id             TEXT UNIQUE NOT NULL,
    estado                TEXT NOT NULL DEFAULT 'ABIERTO',
    fuente                TEXT,
    categoria             TEXT,                  -- ELITE | CRITICO | VIGILANCIA
    prioridad             TEXT,                  -- P0 | P1 | P2 (string en v5.5)
    color                 TEXT,
    accion_recomendada    TEXT,
    escalar_a             TEXT,

    creado_en             TIMESTAMPTZ DEFAULT NOW(),
    fecha_creacion        TIMESTAMPTZ DEFAULT NOW(),
    sla_deadline          TIMESTAMPTZ,
    sla_horas             INT,
    resuelto_en           TIMESTAMPTZ,
    resuelto_por          TEXT,

    activo                TEXT,
    operador              TEXT,
    tipo_activo           TEXT,
    latitud               DOUBLE PRECISION,
    longitud              DOUBLE PRECISION,
    fecha_deteccion       TIMESTAMPTZ,
    ch4_ppb               DOUBLE PRECISION,
    ch4_anomaly_ppb       DOUBLE PRECISION,
    score                 DOUBLE PRECISION,
    perdida_usd_dia       DOUBLE PRECISION,
    viento_velocidad      DOUBLE PRECISION,
    viento_direccion      DOUBLE PRECISION,

    asignado_a            TEXT,
    notas                 JSONB DEFAULT '[]'::jsonb,
    historial             JSONB DEFAULT '[]'::jsonb,
    fuente_datos          TEXT
);

-- 4. Índices para queries comunes
CREATE INDEX idx_tickets_estado     ON tickets(estado);
CREATE INDEX idx_tickets_categoria  ON tickets(categoria);
CREATE INDEX idx_tickets_activo     ON tickets(activo);
CREATE INDEX idx_tickets_creado_en  ON tickets(creado_en DESC);
CREATE INDEX idx_tickets_sla        ON tickets(sla_deadline)
    WHERE estado = 'ABIERTO';

-- 5. RLS (Row Level Security) — si usas Supabase Auth.
-- Si NO usas RLS (la app va con service_role_key), comenta este bloque.
-- ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "tickets_read_all" ON tickets FOR SELECT USING (true);
-- CREATE POLICY "tickets_insert_service" ON tickets FOR INSERT WITH CHECK (true);
-- CREATE POLICY "tickets_update_service" ON tickets FOR UPDATE USING (true);

-- 6. Verificar
SELECT
    'Tabla tickets v5.5 creada' AS status,
    count(*) AS total_tickets
FROM tickets;
