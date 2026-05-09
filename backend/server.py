"""Entrypoint FastAPI — METAvision API (Fase 1)."""
from pathlib import Path

from dotenv import load_dotenv

# Cargar .env ANTES de cualquier otro import que lea variables de entorno.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio  # noqa: E402
import logging  # noqa: E402

from fastapi import APIRouter, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from app.auth.routes import router as auth_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.core.middleware import RequestContextMiddleware  # noqa: E402
from app.db.mongo import close_db  # noqa: E402
from app.db.seed import run_seed  # noqa: E402
from app.routes.admin import router as admin_router  # noqa: E402
from app.routes.alerts import router as alerts_router  # noqa: E402
from app.routes.detections import router as detections_router  # noqa: E402
from app.routes.health import router as health_router  # noqa: E402
from app.routes.inference import model_router, router as inference_router  # noqa: E402
from app.routes.pipelines import router as pipelines_router  # noqa: E402
from app.routes.reports import router as reports_router  # noqa: E402
from app.routes.stations import router as stations_router  # noqa: E402
from app.routes.stats import router as stats_router  # noqa: E402
from app.routes.wells import router as wells_router  # noqa: E402
from app.routes.wind import router as wind_router  # noqa: E402
from app.services.simulator import run_simulator_loop  # noqa: E402
from app.ws.routes import router as ws_router  # noqa: E402
from app.routes.trpc import router as trpc_router  # noqa: E402

setup_logging()
log = logging.getLogger("metavision")

app = FastAPI(
    title="METAvision API",
    description=(
        "Backend del dashboard **METAvision** — Inteligencia Geoespacial del Metano "
        "(Magdalena Medio, Colombia).\n\nMotor de IA interno: MetanoSRGAN Elite v2.1."
    ),
    version="5.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

# Todo bajo /api (ingress lo exige)
api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(stations_router)
api_router.include_router(wells_router)
api_router.include_router(pipelines_router)
api_router.include_router(detections_router)
api_router.include_router(wind_router)
api_router.include_router(alerts_router)
api_router.include_router(inference_router)
api_router.include_router(model_router)
api_router.include_router(reports_router)
api_router.include_router(stats_router)
api_router.include_router(admin_router)
api_router.include_router(ws_router)  # WS también bajo /api
api_router.include_router(trpc_router)  # tRPC procedures
app.include_router(api_router)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _on_startup() -> None:
    log.info(
        "Starting %s v%s (auth_provider=%s, simulate_alerts=%s)",
        settings.app_name, settings.app_version,
        settings.auth_provider, settings.simulate_alerts,
    )
    try:
        await run_seed()
        log.info("Seed completed")
    except Exception:  # noqa: BLE001
        log.exception("Seed failed")

    # Lanzar simulador como task (si está habilitado)
    if settings.simulate_alerts:
        app.state.sim_task = asyncio.create_task(run_simulator_loop())
    else:
        app.state.sim_task = None


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    task = getattr(app.state, "sim_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    await close_db()
    log.info("Mongo client closed")
