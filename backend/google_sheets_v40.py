"""
google_sheets_v40.py — Integración con Google Sheets para MetanoSRGAN Elite v4.0
Permite enviar reportes automáticos de detecciones a una hoja de cálculo.
"""
import os
import json
import logging
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

class GoogleSheetsReporter:
    def __init__(self, credentials_path="credentials.json", spreadsheet_name="MetanoSRGAN_Reportes"):
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None
        self.setup_client()
        
    def setup_client(self):
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"No se encontró el archivo de credenciales en {self.credentials_path}")
                return
                
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
            self.client = gspread.authorize(creds)
            
            # Intentar abrir la hoja, o crearla si no existe
            try:
                self.sheet = self.client.open(self.spreadsheet_name).sheet1
            except gspread.exceptions.SpreadsheetNotFound:
                logger.info(f"Creando nueva hoja de cálculo: {self.spreadsheet_name}")
                new_sheet = self.client.create(self.spreadsheet_name)
                self.sheet = new_sheet.sheet1
                # Configurar cabeceras
                headers = ["Fecha", "Activo", "CH4_Total(ppb)", "CH4_Anomalia(ppb)", "Elite_Score", "Pérdida_USD_Dia", "Categoría"]
                self.sheet.append_row(headers)
                
            logger.info("✓ Conexión a Google Sheets establecida")
        except Exception as e:
            logger.error(f"Error conectando a Google Sheets: {e}")
            
    def report_detection(self, detection_data):
        if not self.sheet:
            logger.warning("Cliente Google Sheets no inicializado.")
            return False
            
        try:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                detection_data.get("activo_cercano", "Desconocido"),
                detection_data.get("ch4_ppb_total", 0),
                detection_data.get("ch4_ppb_anomaly", 0),
                detection_data.get("elite_score", 0),
                detection_data.get("perdida_economica_usd_dia", 0),
                detection_data.get("categoria_alerta", "NORMAL")
            ]
            self.sheet.append_row(row)
            logger.info(f"Detección reportada en Google Sheets: {detection_data.get('activo_cercano')}")
            return True
        except Exception as e:
            logger.error(f"Error reportando en Google Sheets: {e}")
            return False
