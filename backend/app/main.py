from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.router import api_router
from app.core.config import settings
from app.middleware.metrics import PrometheusMiddleware
from app.services.metrics_collector import start_metrics_collector, stop_metrics_collector
from app.services.prometheus_node_sync import start_prometheus_node_sync, stop_prometheus_node_sync
from app.services.prometheus_targets import start_prometheus_targets_writer, stop_prometheus_targets_writer
from app.services.sync_scheduler import start_auto_sync_scheduler, stop_auto_sync_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_auto_sync_scheduler()
    start_metrics_collector()
    start_prometheus_targets_writer()
    start_prometheus_node_sync()
    yield
    await stop_prometheus_node_sync()
    await stop_prometheus_targets_writer()
    await stop_metrics_collector()
    await stop_auto_sync_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Lightweight HomeLab management platform for DevOps users",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware)

app.mount("/metrics", make_asgi_app())
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
