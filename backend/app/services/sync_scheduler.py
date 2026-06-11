import asyncio
import logging

from app.core.database import SessionLocal
from app.services.container_auto_sync import run_containers_auto_sync_async
from app.services.sync_settings_service import get_or_create_sync_settings

logger = logging.getLogger(__name__)

INITIAL_DELAY_SECONDS = 60
_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


async def _auto_sync_loop() -> None:
    assert _stop_event is not None
    await asyncio.sleep(INITIAL_DELAY_SECONDS)

    while not _stop_event.is_set():
        interval = 300
        try:
            db = SessionLocal()
            try:
                settings = get_or_create_sync_settings(db)
                interval = max(60, settings.containers_sync_interval_seconds)
                enabled = settings.containers_auto_sync_enabled
            finally:
                db.close()

            if enabled:
                result = await run_containers_auto_sync_async()
                if not result.skipped:
                    logger.info("Container auto-sync: %s", result.summary)
        except Exception:
            logger.exception("Container auto-sync loop error")

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue


def start_auto_sync_scheduler() -> asyncio.Task:
    global _task, _stop_event
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_auto_sync_loop(), name="container-auto-sync")
    logger.info("Container auto-sync scheduler started")
    return _task


async def stop_auto_sync_scheduler() -> None:
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
    logger.info("Container auto-sync scheduler stopped")
