"""
metano_alerts_bot_v40.py — MetanoSRGAN Elite v4.0
Bot de Telegram con Webhooks y Gráficas Integradas
"""
import os
import sys
import json
import logging
import asyncio
import requests
import io
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ─── Configuración ────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8697859059:AAGIvGErN1E764bvQ1sYcc5vHZNFYKAsOkY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # URL del backend en Render/Vercel
PORT = int(os.getenv("PORT", "8443"))

BASE_DIR = Path(__file__).parent.parent
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MetanoAlertsBotV4")

# ─── Comandos ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    msg = (
        f"👋 ¡Hola {user.first_name}! Bienvenido a **MetanoSRGAN Elite v4.0**.\n\n"
        "Soy tu asistente de monitoreo satelital de metano. Estoy conectado 24/7 "
        "para alertarte sobre emisiones críticas.\n\n"
        "Usa /ayuda para ver los comandos disponibles."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda"""
    msg = (
        "🛠 **Comandos Disponibles:**\n\n"
        "/start - Iniciar bot\n"
        "/estado - Estado del sistema\n"
        "/grafica - Ver gráfica de emisiones recientes\n"
        "/resumen - Resumen ejecutivo\n"
        "/ayuda - Esta ayuda"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def grafica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera y envía una gráfica de emisiones (v4.0)"""
    await update.message.reply_text("📊 Generando gráfica de emisiones recientes...", parse_mode="Markdown")
    
    try:
        # Generar gráfica de ejemplo
        plt.figure(figsize=(10, 5))
        activos = ['Galán (TGI)', 'Cusiana', 'Apiay', 'Cupia', 'Cupiagua']
        valores = [265.8, 120.4, 85.2, 45.1, 30.0]
        
        plt.bar(activos, valores, color=['#ff4444', '#ff8800', '#ffcc00', '#00cc66', '#00cc66'])
        plt.title('Emisiones de Metano por Activo (Anomalía ppb) - v4.0')
        plt.ylabel('Anomalía CH4 (ppb)')
        plt.xlabel('Activo Monitoreado')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Guardar en buffer de memoria
        buf = io.BytesBytesIO() if hasattr(io, 'BytesIO') else io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        
        await update.message.reply_photo(photo=buf, caption="📈 **Gráfica de Anomalías de Metano (Último Ciclo)**", parse_mode="Markdown")
        plt.close()
    except Exception as e:
        logger.error(f"Error generando gráfica: {e}")
        await update.message.reply_text("❌ Error generando la gráfica. Por favor, intenta más tarde.")

# ─── Webhook Setup ────────────────────────────────────────────────────────────
def main():
    """Inicia el bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("grafica", grafica))

    if False:  # Forzar Polling para Render Worker
        # Modo Webhook (Producción)
        logger.info(f"Iniciando en modo WEBHOOK en {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{WEBHOOK_URL}/telegram-webhook"
        )
    else:
        # Modo Polling (Desarrollo)
        logger.info("Iniciando en modo POLLING")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
