import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import PROMETHEUS_TARGETS
from app.models.node import Node

logger = logging.getLogger(__name__)

NODE_EXPORTER_PORT = 9100
REFRESH_INTERVAL_SECONDS = 60
_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None
_last_updated_at: datetime | None = None


def _targets_path() -> Path:
    return Path(settings.PROMETHEUS_FILE_SD_DIR) / "nodes.json"


def build_node_exporter_targets(db: Session) -> list[dict]:
    targets: list[dict] = []
    for node in db.query(Node).order_by(Node.name).all():
        targets.append(
            {
                "targets": [f"{node.ip_address}:{NODE_EXPORTER_PORT}"],
                "labels": {
                    "node": node.name,
                    "instance": node.name,
                    "opsdeck_node_id": str(node.id),
                },
            }
        )
    return targets


def write_prometheus_targets(db: Session | None = None) -> int:
    global _last_updated_at
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        targets = build_node_exporter_targets(db)
        path = _targets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
        _last_updated_at = datetime.utcnow()
        PROMETHEUS_TARGETS.set(len(targets))
        logger.info("Wrote %d Prometheus node_exporter target(s) to %s", len(targets), path)
        return len(targets)
    except Exception:
        logger.exception("Failed to write Prometheus file_sd targets")
        return 0
    finally:
        if own_db and db is not None:
            db.close()


def get_targets_status() -> dict:
    path = _targets_path()
    targets: list[dict] = []
    if path.exists():
        try:
            targets = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            targets = []
    return {
        "targets_count": len(targets),
        "targets": targets,
        "targets_file": str(path),
        "updated_at": _last_updated_at,
    }


async def _targets_loop() -> None:
    assert _stop_event is not None
    while not _stop_event.is_set():
        await asyncio.to_thread(write_prometheus_targets)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=REFRESH_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            continue


def start_prometheus_targets_writer() -> asyncio.Task:
    global _task, _stop_event
    write_prometheus_targets()
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_targets_loop(), name="prometheus-targets")
    logger.info("Prometheus targets writer started")
    return _task


async def stop_prometheus_targets_writer() -> None:
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
    logger.info("Prometheus targets writer stopped")
