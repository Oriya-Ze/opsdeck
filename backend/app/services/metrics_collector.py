import asyncio
import logging

from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.metrics import (
    APP_INFO,
    CONTAINERS_TOTAL,
    NODES_TOTAL,
    SERVICES_TOTAL,
)
from app.core.config import settings
from app.models.container import Container
from app.models.node import Node
from app.models.service import Service

logger = logging.getLogger(__name__)

COLLECT_INTERVAL_SECONDS = 60
_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


def collect_metrics_snapshot() -> None:
    db = SessionLocal()
    try:
        APP_INFO.info({"version": settings.APP_VERSION, "app": settings.APP_NAME})

        for status, count in (
            db.query(Node.status, func.count(Node.id)).group_by(Node.status).all()
        ):
            NODES_TOTAL.labels(status=status or "unknown").set(count)

        for status, count in (
            db.query(Service.status, func.count(Service.id)).group_by(Service.status).all()
        ):
            SERVICES_TOTAL.labels(status=status or "unknown").set(count)

        for status, count in (
            db.query(Container.status, func.count(Container.id)).group_by(Container.status).all()
        ):
            CONTAINERS_TOTAL.labels(status=status or "unknown").set(count)
    except Exception:
        logger.exception("Failed to collect OpsDeck metrics snapshot")
    finally:
        db.close()


async def _metrics_loop() -> None:
    assert _stop_event is not None
    while not _stop_event.is_set():
        await asyncio.to_thread(collect_metrics_snapshot)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=COLLECT_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            continue


def start_metrics_collector() -> asyncio.Task:
    global _task, _stop_event
    collect_metrics_snapshot()
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_metrics_loop(), name="metrics-collector")
    logger.info("Metrics collector started")
    return _task


async def stop_metrics_collector() -> None:
    global _task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
    _stop_event = None
    logger.info("Metrics collector stopped")
