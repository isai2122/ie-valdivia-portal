"""
netcdf_sentinel5p_v36.py — MetanoSRGAN Elite v3.6
Integración directa de productos NetCDF de Sentinel-5P desde Copernicus Data Space.

Descarga y procesa productos reales S5P_OFFL_L2__CH4___ en formato NetCDF-4.
Requiere credenciales registradas en: https://identity.dataspace.copernicus.eu/

Flujo:
  1. Autenticación OAuth2 con Copernicus Data Space Ecosystem (CDSE)
  2. Búsqueda de productos S5P L2 CH4 sobre el área de interés (Magdalena Medio)
  3. Descarga del archivo .nc (NetCDF-4)
  4. Extracción de columna total de CH4 (XCH4) en ppb
  5. Reproyección y recorte al área de interés
  6. Entrega de datos estructurados al pipeline principal
"""

import os
import json
import logging
import requests
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_CATALOG_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

# Área de interés: Magdalena Medio, Colombia
# Bounding box: [lon_min, lat_min, lon_max, lat_max]
AOI_BBOX = {
    "lon_min": -75.5,
    "lat_min":  4.5,
    "lon_max": -72.5,
    "lat_max":  8.0,
}

# Infraestructura monitoreada
INFRAESTRUCTURA = [
    {"nombre": "Vasconia",        "lat": 5.918,  "lon": -74.475, "tipo": "Compresión",  "operador": "TGI"},
    {"nombre": "Barrancabermeja", "lat": 7.065,  "lon": -73.850, "tipo": "Refinería",   "operador": "Ecopetrol"},
    {"nombre": "Sebastopol",      "lat": 5.820,  "lon": -74.180, "tipo": "Compresión",  "operador": "TGI"},
    {"nombre": "Malena",          "lat": 6.490,  "lon": -74.405, "tipo": "Compresión",  "operador": "TGI"},
    {"nombre": "Mariquita",       "lat": 5.204,  "lon": -74.895, "tipo": "Compresión",  "operador": "TGI"},
    {"nombre": "Casabe",          "lat": 6.750,  "lon": -73.980, "tipo": "Producción",  "operador": "Ecopetrol"},
    {"nombre": "Norean",          "lat": 7.200,  "lon": -73.650, "tipo": "Producción",  "operador": "Ecopetrol"},
    {"nombre": "Miraflores",      "lat": 5.210,  "lon": -73.145, "tipo": "Producción",  "operador": "Ecopetrol"},
    {"nombre": "Galán",           "lat": 6.890,  "lon": -73.720, "tipo": "Compresión",  "operador": "TGI"},
    {"nombre": "Payoa",           "lat": 7.050,  "lon": -73.480, "tipo": "Producción",  "operador": "Ecopetrol"},
]

CH4_BACKGROUND_PPB = 1920.0


class CopernicusNetCDFClient:
    """
    Cliente para descarga y procesamiento de productos NetCDF Sentinel-5P.
    Utiliza la API OAuth2 de Copernicus Data Space Ecosystem (CDSE).
    """

    def __init__(
        self,
        username: str = "",
        password: str = "",
        data_dir: str = "/home/ubuntu/metanosrgan_v36/data/netcdf",
    ):
        self.username = username or os.getenv("COPERNICUS_USER", "")
        self.password = password or os.getenv("COPERNICUS_PASS", "")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MetanoSRGAN-Elite/3.6 (Ecopetrol Methane Monitor)"
        })

    # ─── Autenticación OAuth2 ─────────────────────────────────────────────────
    def authenticate(self) -> bool:
        """
        Obtiene token de acceso OAuth2 de Copernicus Data Space.
        Retorna True si la autenticación fue exitosa.
        """
        if not self.username or not self.password:
            logger.warning(
                "Credenciales Copernicus no configuradas. "
                "Establece COPERNICUS_USER y COPERNICUS_PASS en .env"
            )
            return False

        try:
            resp = self.session.post(
                CDSE_TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                    "client_id": "cdse-public",
                },
                timeout=30,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 600)
            self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
            self.session.headers.update({"Authorization": f"Bearer {self._access_token}"})
            logger.info("Autenticación Copernicus exitosa.")
            return True
        except Exception as e:
            logger.error(f"Error de autenticación Copernicus: {e}")
            return False

    def _ensure_token(self) -> bool:
        """Renueva el token si está próximo a expirar."""
        if self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return True
        return self.authenticate()

    # ─── Búsqueda de productos ────────────────────────────────────────────────
    def search_products(
        self,
        days_back: int = 7,
        max_results: int = 5,
    ) -> List[Dict]:
        """
        Busca productos S5P L2 CH4 disponibles sobre el Magdalena Medio.

        Args:
            days_back: Cuántos días hacia atrás buscar.
            max_results: Máximo de productos a retornar.

        Returns:
            Lista de diccionarios con metadatos de productos encontrados.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        bbox_wkt = (
            f"POLYGON(("
            f"{AOI_BBOX['lon_min']} {AOI_BBOX['lat_min']},"
            f"{AOI_BBOX['lon_max']} {AOI_BBOX['lat_min']},"
            f"{AOI_BBOX['lon_max']} {AOI_BBOX['lat_max']},"
            f"{AOI_BBOX['lon_min']} {AOI_BBOX['lat_max']},"
            f"{AOI_BBOX['lon_min']} {AOI_BBOX['lat_min']}"
            f"))"
        )

        filter_query = (
            f"Collection/Name eq 'SENTINEL-5P' "
            f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
            f"and att/OData.CSC.StringAttribute/Value eq 'L2__CH4___') "
            f"and ContentDate/Start gt {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"and ContentDate/Start lt {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{bbox_wkt}')"
        )

        try:
            resp = self.session.get(
                CDSE_CATALOG_URL,
                params={
                    "$filter": filter_query,
                    "$orderby": "ContentDate/Start desc",
                    "$top": max_results,
                    "$expand": "Attributes",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            products = data.get("value", [])
            logger.info(f"Encontrados {len(products)} productos S5P CH4 en el área de interés.")
            return products
        except Exception as e:
            logger.error(f"Error buscando productos Copernicus: {e}")
            return []

    # ─── Descarga de productos ────────────────────────────────────────────────
    def download_product(self, product: Dict) -> Optional[str]:
        """
        Descarga un producto NetCDF de Sentinel-5P.

        Args:
            product: Diccionario con metadatos del producto (de search_products).

        Returns:
            Ruta local al archivo .nc descargado, o None si falló.
        """
        if not self._ensure_token():
            logger.error("No se puede descargar sin autenticación válida.")
            return None

        product_id = product.get("Id", "")
        product_name = product.get("Name", product_id)
        local_path = os.path.join(self.data_dir, f"{product_name}.nc")

        if os.path.exists(local_path):
            logger.info(f"Producto ya descargado: {local_path}")
            return local_path

        try:
            download_url = f"{CDSE_DOWNLOAD_URL}({product_id})/$value"
            logger.info(f"Descargando producto: {product_name}")

            with self.session.get(download_url, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

            size_mb = os.path.getsize(local_path) / 1024 / 1024
            logger.info(f"Descarga completa: {local_path} ({size_mb:.1f} MB)")
            return local_path
        except Exception as e:
            logger.error(f"Error descargando producto {product_name}: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            return None

    # ─── Procesamiento NetCDF ─────────────────────────────────────────────────
    def process_netcdf(self, nc_path: str) -> List[Dict]:
        """
        Procesa un archivo NetCDF de Sentinel-5P y extrae CH4 (XCH4) en ppb
        para cada punto de infraestructura del Magdalena Medio.

        El producto S5P L2 CH4 contiene:
          - /PRODUCT/methane_mixing_ratio_bias_corrected  [mol/mol]
          - /PRODUCT/latitude, /PRODUCT/longitude
          - /PRODUCT/qa_value  [0-1, usar >= 0.5]

        Args:
            nc_path: Ruta al archivo .nc descargado.

        Returns:
            Lista de detecciones con CH4 en ppb por punto de infraestructura.
        """
        try:
            import netCDF4 as nc
        except ImportError:
            logger.error("netCDF4 no instalado. Ejecutar: pip install netCDF4")
            return self._fallback_openmeteo()

        try:
            logger.info(f"Procesando NetCDF: {nc_path}")
            ds = nc.Dataset(nc_path, "r")

            # Variables del producto S5P L2 CH4
            product_group = ds.groups.get("PRODUCT", ds)
            lats = np.array(product_group.variables["latitude"][:]).flatten()
            lons = np.array(product_group.variables["longitude"][:]).flatten()
            ch4_raw = np.array(product_group.variables["methane_mixing_ratio_bias_corrected"][:]).flatten()
            qa = np.array(product_group.variables["qa_value"][:]).flatten()

            # Filtrar por calidad (qa >= 0.5 recomendado por ESA)
            valid_mask = (qa >= 0.5) & (~np.isnan(ch4_raw)) & (ch4_raw > 0)
            lats_valid = lats[valid_mask]
            lons_valid = lons[valid_mask]
            ch4_valid = ch4_raw[valid_mask]  # mol/mol → ppb: × 1e9

            # Convertir mol/mol a ppb
            ch4_ppb_valid = ch4_valid * 1e9

            ds.close()
            logger.info(
                f"NetCDF procesado: {len(ch4_ppb_valid)} píxeles válidos "
                f"(QA≥0.5), rango CH4: {ch4_ppb_valid.min():.0f}–{ch4_ppb_valid.max():.0f} ppb"
            )

            # Extraer valor más cercano a cada punto de infraestructura
            detections = []
            for activo in INFRAESTRUCTURA:
                lat_a, lon_a = activo["lat"], activo["lon"]
                distances = np.sqrt((lats_valid - lat_a) ** 2 + (lons_valid - lon_a) ** 2)
                if len(distances) == 0:
                    continue
                idx_min = np.argmin(distances)
                dist_deg = distances[idx_min]
                dist_km = dist_deg * 111.0  # aprox. km

                # Solo usar si el pixel más cercano está dentro de ~50 km
                if dist_km > 50:
                    logger.debug(f"{activo['nombre']}: sin cobertura S5P (dist={dist_km:.0f} km)")
                    continue

                ch4_ppb = float(ch4_ppb_valid[idx_min])
                anomaly = max(0.0, ch4_ppb - CH4_BACKGROUND_PPB)

                detections.append({
                    "nombre": activo["nombre"],
                    "lat": lat_a,
                    "lon": lon_a,
                    "tipo": activo["tipo"],
                    "operador": activo["operador"],
                    "ch4_ppb_total": round(ch4_ppb, 1),
                    "ch4_ppb_anomaly": round(anomaly, 1),
                    "fuente": "Sentinel-5P NetCDF (CDSE)",
                    "producto": os.path.basename(nc_path),
                    "dist_pixel_km": round(dist_km, 1),
                    "qa_value": float(qa[valid_mask][idx_min]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "resolucion_original_km": 5.5,
                })

            logger.info(f"Extraídas {len(detections)} detecciones desde NetCDF.")
            return detections

        except Exception as e:
            logger.error(f"Error procesando NetCDF {nc_path}: {e}")
            return self._fallback_openmeteo()

    # ─── Fallback: Open-Meteo (sin credenciales) ──────────────────────────────
    def _fallback_openmeteo(self) -> List[Dict]:
        """
        Fallback a Open-Meteo Air Quality API cuando no hay credenciales
        Copernicus o el NetCDF no está disponible.
        Mantiene compatibilidad con el pipeline v3.5.
        """
        logger.info("Usando fallback Open-Meteo Air Quality (CAMS data).")
        AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
        detections = []

        for activo in INFRAESTRUCTURA:
            try:
                resp = requests.get(
                    AQ_URL,
                    params={
                        "latitude": activo["lat"],
                        "longitude": activo["lon"],
                        "hourly": "methane",
                        "timezone": "America/Bogota",
                        "past_days": 1,
                        "forecast_days": 0,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                hourly = data.get("hourly", {})
                values = hourly.get("methane", [])
                valid_vals = [v for v in values if v is not None and v > 0]
                if not valid_vals:
                    continue
                # Convertir µg/m³ → ppb (÷ 0.716 para CH4 a 25°C, 1 atm)
                ch4_ppb = float(np.mean(valid_vals)) / 0.716
                anomaly = max(0.0, ch4_ppb - CH4_BACKGROUND_PPB)

                detections.append({
                    "nombre": activo["nombre"],
                    "lat": activo["lat"],
                    "lon": activo["lon"],
                    "tipo": activo["tipo"],
                    "operador": activo["operador"],
                    "ch4_ppb_total": round(ch4_ppb, 1),
                    "ch4_ppb_anomaly": round(anomaly, 1),
                    "fuente": "Open-Meteo Air Quality (CAMS fallback)",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "resolucion_original_km": 40.0,  # CAMS resolución ~40 km
                })
            except Exception as e:
                logger.warning(f"Open-Meteo fallback error para {activo['nombre']}: {e}")

        logger.info(f"Fallback Open-Meteo: {len(detections)} puntos obtenidos.")
        return detections

    # ─── Método principal ─────────────────────────────────────────────────────
    def get_ch4_data(self, days_back: int = 3) -> List[Dict]:
        """
        Método principal: intenta descarga NetCDF real, cae a fallback si no hay credenciales.

        Args:
            days_back: Días hacia atrás para buscar productos.

        Returns:
            Lista de detecciones con CH4 en ppb.
        """
        # Intentar con credenciales reales
        if self.username and self.password:
            if self.authenticate():
                products = self.search_products(days_back=days_back, max_results=3)
                if products:
                    nc_path = self.download_product(products[0])
                    if nc_path:
                        detections = self.process_netcdf(nc_path)
                        if detections:
                            logger.info(
                                f"Datos NetCDF reales obtenidos: {len(detections)} puntos "
                                f"desde {products[0].get('Name', 'S5P producto')}"
                            )
                            return detections

        # Fallback a Open-Meteo
        return self._fallback_openmeteo()

    # ─── Guardar metadatos de descarga ────────────────────────────────────────
    def save_download_log(self, products: List[Dict], output_path: str):
        """Guarda log de productos descargados para auditoría."""
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "products_found": len(products),
            "products": [
                {
                    "id": p.get("Id"),
                    "name": p.get("Name"),
                    "date": p.get("ContentDate", {}).get("Start"),
                    "size_mb": round(p.get("ContentLength", 0) / 1024 / 1024, 1),
                }
                for p in products
            ],
        }
        with open(output_path, "w") as f:
            json.dump(log, f, indent=2)
        logger.info(f"Log de descarga guardado: {output_path}")
