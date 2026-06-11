from prometheus_client import Counter, Gauge, Histogram, Info

APP_INFO = Info("opsdeck", "OpsDeck application information")

NODES_TOTAL = Gauge(
    "opsdeck_nodes_total",
    "Number of managed nodes",
    ["status"],
)
SERVICES_TOTAL = Gauge(
    "opsdeck_services_total",
    "Number of monitored services",
    ["status"],
)
CONTAINERS_TOTAL = Gauge(
    "opsdeck_containers_total",
    "Number of synced Docker containers",
    ["status"],
)

CONTAINER_SYNC_RUNS = Counter(
    "opsdeck_container_sync_runs_total",
    "Total container auto-sync runs",
)
CONTAINER_SYNC_NODES = Counter(
    "opsdeck_container_sync_nodes_total",
    "Nodes processed during container sync",
    ["result"],
)

HTTP_REQUESTS = Counter(
    "opsdeck_http_requests_total",
    "HTTP requests to the OpsDeck API",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "opsdeck_http_request_duration_seconds",
    "HTTP request latency for the OpsDeck API",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

PROMETHEUS_TARGETS = Gauge(
    "opsdeck_prometheus_scrape_targets",
    "Number of node_exporter targets registered for Prometheus",
)
