"""Configuración leída desde variables de entorno."""
import os


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    mongo_url: str = os.environ["MONGO_URL"]
    db_name: str = os.environ["DB_NAME"]
    cors_origins: str = os.environ.get("CORS_ORIGINS", "*")

    jwt_secret: str = os.environ["JWT_SECRET"]
    jwt_alg: str = os.environ.get("JWT_ALG", "HS256")
    jwt_expires_hours: int = int(os.environ.get("JWT_EXPIRES_HOURS", "12"))

    auth_provider: str = os.environ.get("AUTH_PROVIDER", "local").lower()

    simulate_alerts: bool = _bool(os.environ.get("SIMULATE_ALERTS"), True)
    simulator_min_interval_s: int = int(os.environ.get("SIM_MIN_S", "45"))
    simulator_max_interval_s: int = int(os.environ.get("SIM_MAX_S", "90"))

    # Bbox operativo del Magdalena Medio: minLng, minLat, maxLng, maxLat
    mm_bbox: tuple[float, float, float, float] = (-75.5, 5.0, -73.0, 8.0)

    app_name: str = "metavision-api"
    app_version: str = "0.2.0"
    product_name: str = "METAvision"
    product_tagline: str = "Dashboard de Inteligencia Geoespacial del Metano"
    # Nombre interno del modelo (no cambiar, es el engine)
    model_name: str = "MetanoSRGAN Elite v2.1"


settings = Settings()
