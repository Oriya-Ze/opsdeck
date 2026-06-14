import asyncio
import logging

from app.core.database import SessionLocal
from app.services.backup_service import run_auto_backups
from app.services.backup_settings_service import get_or_create_backup_settings

logger = logging.getLogger(__name__)

INITIAL_DELAY_SECONDS = 120
_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


async def _auto_backup_loop() -> None:
    assert _stop_event is not None
    await asyncio.sleep(INITIAL_DELAY_SECONDS)

    while not _stop_event.is_set():
        interval = 86400
        try:
            db = SessionLocal()
            try:
                settings = get_or_create_backup_settings(db)
                interval = max(3600, settings.backup_interval_seconds)
                enabled = settings.auto_backup_enabled
            finally:
                db.close()

            if enabled:
                result = await asyncio.to_thread(_run_auto_backups_sync)
                if not result.skipped:
                    logger.info("Node auto-backup: %s", result.summary)
        except Exception:
            logger.exception("Node auto-backup loop error")

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue


def _run_auto_backups_sync():
    db = SessionLocal()
    try:
        return run_auto_backups(db)
    finally:
        db.close()


def start_auto_backup_scheduler() -> asyncio.Task:
    global _task, _stop_event
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_auto_backup_loop(), name="node-auto-backup")
    logger.info("Node auto-backup scheduler started")
    return _task


async def stop_auto_backup_scheduler() -> None:
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
    logger.info("Node auto-backup scheduler stopped")
