import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)


class PrometheusApiError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _request(path: str, params: dict | None = None) -> dict:
    base = settings.PROMETHEUS_INTERNAL_URL.rstrip("/")
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise PrometheusApiError(f"Prometheus HTTP {exc.code}: {body}", exc.code) from exc
    except urllib.error.URLError as exc:
        raise PrometheusApiError(f"Prometheus unreachable: {exc.reason}") from exc

    if payload.get("status") != "success":
        raise PrometheusApiError(payload.get("error", "Prometheus query failed"))
    return payload


def query_instant(promql: str) -> dict:
    return _request("/api/v1/query", {"query": promql})


def query_range(promql: str, start: float, end: float, step: str) -> dict:
    return _request(
        "/api/v1/query_range",
        {
            "query": promql,
            "start": str(start),
            "end": str(end),
            "step": step,
        },
    )


def get_targets() -> dict:
    return _request("/api/v1/targets")


def _scalar_value(result: dict) -> float | None:
    data = result.get("data", {}).get("result", [])
    if not data:
        return None
    value = data[0].get("value")
    if not value or len(value) < 2:
        return None
    try:
        return float(value[1])
    except (TypeError, ValueError):
        return None


def get_overview_metrics() -> dict:
    queries = {
        "healthy_nodes": 'sum(opsdeck_nodes_total{status="healthy"})',
        "running_containers": 'sum(opsdeck_containers_total{status="running"})',
        "up_services": 'sum(opsdeck_services_total{status="up"})',
        "scrape_targets": "opsdeck_prometheus_scrape_targets",
        "sync_runs_hour": "increase(opsdeck_container_sync_runs_total[1h])",
        "api_request_rate": "sum(rate(opsdeck_http_requests_total[5m]))",
        "node_exporters_up": 'count(up{job="node_exporter"} == 1)',
        "node_exporters_total": 'count(up{job="node_exporter"})',
    }

    metrics: dict[str, float | None] = {}
    for key, promql in queries.items():
        try:
            metrics[key] = _scalar_value(query_instant(promql))
        except PrometheusApiError:
            logger.warning("Prometheus overview query failed: %s", key)
            metrics[key] = None
    return metrics
