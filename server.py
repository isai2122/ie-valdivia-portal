"""
server.py (root) — Punto de entrada para Render
================================================
Render usa `uvicorn server:app`. Esto re-exporta la app FastAPI real
ubicada en backend/server.py para mantener una estructura limpia.
"""
import sys
from pathlib import Path

# Asegurar que /app y /app/backend están en sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Importar la aplicación FastAPI canónica
from backend.server import app  # noqa: F401, E402

__all__ = ["app"]
