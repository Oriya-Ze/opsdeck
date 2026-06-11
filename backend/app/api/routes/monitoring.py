import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.monitoring import (
    MonitoringOverviewResponse,
    MonitoringStatusResponse,
    NodePrometheusSyncResponse,
    PrometheusQueryRangeResponse,
    PrometheusSeries,
    PrometheusSeriesPoint,
    ScrapeTargetStatus,
    ScrapeTargetsResponse,
)
from app.services.prometheus_api import PrometheusApiError, get_overview_metrics, get_targets, query_range
from app.services.prometheus_node_sync import sync_nodes_from_prometheus
from app.services.prometheus_targets import build_node_exporter_targets, get_targets_status, write_prometheus_targets

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def _status_response(db: Session) -> MonitoringStatusResponse:
    status = get_targets_status()
    return MonitoringStatusResponse(
        prometheus_url=settings.PROMETHEUS_URL,
        grafana_url=settings.GRAFANA_URL,
        grafana_embed_url=settings.GRAFANA_EMBED_URL,
        node_exporter_port=9100,
        targets_count=status["targets_count"],
        targets=build_node_exporter_targets(db),
        targets_file=status["targets_file"],
        targets_updated_at=status["updated_at"],
    )


def _parse_query_range(payload: dict, query: str) -> PrometheusQueryRangeResponse:
    series: list[PrometheusSeries] = []
    for item in payload.get("data", {}).get("result", []):
        points: list[PrometheusSeriesPoint] = []
        for ts, val in item.get("values", []):
            try:
                points.append(PrometheusSeriesPoint(timestamp=float(ts), value=float(val)))
            except (TypeError, ValueError):
                continue
        series.append(
            PrometheusSeries(
                metric={k: str(v) for k, v in item.get("metric", {}).items()},
                points=points,
            )
        )
    return PrometheusQueryRangeResponse(query=query, series=series)


def _parse_scrape_targets(payload: dict) -> ScrapeTargetsResponse:
    targets: list[ScrapeTargetStatus] = []
    for item in payload.get("data", {}).get("activeTargets", []):
        labels = item.get("labels", {})
        targets.append(
            ScrapeTargetStatus(
                job=labels.get("job", ""),
                instance=labels.get("instance", labels.get("node", "")),
                health=item.get("health", "unknown"),
                scrape_url=item.get("scrapeUrl", ""),
                last_scrape=item.get("lastScrape"),
                last_error=item.get("lastError") or None,
            )
        )

    up = sum(1 for t in targets if t.health == "up")
    down = sum(1 for t in targets if t.health == "down")
    unknown = len(targets) - up - down
    return ScrapeTargetsResponse(targets=targets, up=up, down=down, unknown=unknown)


@router.get("/status", response_model=MonitoringStatusResponse)
def monitoring_status(db: Session = Depends(get_db)):
    return _status_response(db)


@router.post("/targets/refresh", response_model=MonitoringStatusResponse)
def refresh_prometheus_targets(db: Session = Depends(get_db)):
    write_prometheus_targets(db)
    return _status_response(db)


@router.get("/overview", response_model=MonitoringOverviewResponse)
def monitoring_overview():
    try:
        metrics = get_overview_metrics()
        return MonitoringOverviewResponse(
            healthy_nodes=metrics.get("healthy_nodes"),
            running_containers=metrics.get("running_containers"),
            up_services=metrics.get("up_services"),
            scrape_targets=metrics.get("scrape_targets"),
            sync_runs_hour=metrics.get("sync_runs_hour"),
            api_request_rate=metrics.get("api_request_rate"),
            node_exporters_up=metrics.get("node_exporters_up"),
            node_exporters_total=metrics.get("node_exporters_total"),
            prometheus_reachable=True,
        )
    except PrometheusApiError as exc:
        return MonitoringOverviewResponse(
            prometheus_reachable=False,
            prometheus_error=str(exc),
        )


@router.get("/prometheus/targets", response_model=ScrapeTargetsResponse)
def prometheus_scrape_targets():
    try:
        return _parse_scrape_targets(get_targets())
    except PrometheusApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/nodes/sync", response_model=NodePrometheusSyncResponse)
def sync_nodes_from_prometheus_now(db: Session = Depends(get_db)):
    result = sync_nodes_from_prometheus(db)
    return NodePrometheusSyncResponse(
        nodes_attempted=result.nodes_attempted,
        nodes_synced=result.nodes_synced,
        nodes_skipped=result.nodes_skipped,
        nodes_failed=result.nodes_failed,
        summary=result.summary,
        errors=result.errors,
    )


@router.get("/prometheus/query-range", response_model=PrometheusQueryRangeResponse)
def prometheus_query_range(
    query: str = Query(..., min_length=1),
    hours: float = Query(6, ge=0.25, le=168),
    step: str = Query("60s"),
):
    end = time.time()
    start = end - (hours * 3600)
    try:
        payload = query_range(query, start, end, step)
        return _parse_query_range(payload, query)
    except PrometheusApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
