#!/bin/bash
# start_bot.sh — Inicia el bot de Telegram MetanoAlerts
# MetanoSRGAN Elite v4.0

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BOT_SCRIPT="$SCRIPT_DIR/metano_alerts_bot_v40.py"
LOG_FILE="$SCRIPT_DIR/bot.log"
PID_FILE="$SCRIPT_DIR/bot.pid"

echo "============================================================"
echo "MetanoAlerts Bot — MetanoSRGAN Elite v4.0"
echo "Bot: @MetanoAlerts_bot"
echo "============================================================"

# Cargar variables de entorno
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
    echo "✓ Variables de entorno cargadas"
fi

# Verificar Python
if ! command -v python3.11 &> /dev/null; then
    echo "✗ Python 3.11 no encontrado"
    exit 1
fi

# Verificar dependencias
python3.11 -c "import telegram; import supabase" 2>/dev/null || {
    echo "Instalando dependencias..."
    pip3 install python-telegram-bot==20.7 supabase
}

# Detener instancia anterior si existe
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Deteniendo instancia anterior (PID: $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Iniciar bot
echo "Iniciando bot..."
cd "$PROJECT_DIR"
nohup python3.11 "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

sleep 3
if kill -0 "$BOT_PID" 2>/dev/null; then
    echo "✓ Bot iniciado exitosamente (PID: $BOT_PID)"
    echo "✓ Log: $LOG_FILE"
    echo "✓ Para detener: kill $BOT_PID"
else
    echo "✗ Error al iniciar el bot. Revisa el log:"
    tail -20 "$LOG_FILE"
    exit 1
fi
