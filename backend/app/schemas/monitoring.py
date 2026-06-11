from datetime import datetime

from pydantic import BaseModel, Field


class PrometheusTarget(BaseModel):
    targets: list[str]
    labels: dict[str, str]


class MonitoringStatusResponse(BaseModel):
    prometheus_url: str
    grafana_url: str
    grafana_embed_url: str
    node_exporter_port: int
    targets_count: int
    targets: list[PrometheusTarget]
    targets_file: str
    targets_updated_at: datetime | None = None


class MonitoringOverviewResponse(BaseModel):
    healthy_nodes: float | None = None
    running_containers: float | None = None
    up_services: float | None = None
    scrape_targets: float | None = None
    sync_runs_hour: float | None = None
    api_request_rate: float | None = None
    node_exporters_up: float | None = None
    node_exporters_total: float | None = None
    prometheus_reachable: bool = True
    prometheus_error: str | None = None


class ScrapeTargetStatus(BaseModel):
    job: str
    instance: str
    health: str
    scrape_url: str
    last_scrape: str | None = None
    last_error: str | None = None


class ScrapeTargetsResponse(BaseModel):
    targets: list[ScrapeTargetStatus]
    up: int
    down: int
    unknown: int


class PrometheusSeriesPoint(BaseModel):
    timestamp: float
    value: float


class PrometheusSeries(BaseModel):
    metric: dict[str, str]
    points: list[PrometheusSeriesPoint]


class PrometheusQueryRangeResponse(BaseModel):
    query: str
    series: list[PrometheusSeries]


class NodePrometheusSyncResponse(BaseModel):
    nodes_attempted: int
    nodes_synced: int
    nodes_skipped: int
    nodes_failed: int
    summary: str
    errors: list[str]
