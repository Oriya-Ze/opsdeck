import enum


class NodeEnvironment(str, enum.Enum):
    LOCAL = "local"
    AWS = "aws"
    LAB = "lab"


class NodeRole(str, enum.Enum):
    MASTER = "master"
    WORKER = "worker"
    VM = "vm"
    RASPBERRY_PI = "raspberry-pi"
    SERVER = "server"


class NodeStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class ServiceProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"


class ServiceStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ServiceCategory(str, enum.Enum):
    MONITORING = "monitoring"
    DATABASE = "database"
    PROXY = "proxy"
    STORAGE = "storage"
    CI_CD = "ci-cd"
    GITOPS = "gitops"
    APP = "app"
    OTHER = "other"


class ContainerStatus(str, enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    FAILED = "failed"
    UNKNOWN = "unknown"


class WorkloadKind(str, enum.Enum):
    DEPLOYMENT = "deployment"
    STATEFULSET = "statefulset"
    DAEMONSET = "daemonset"
    POD = "pod"
    SERVICE = "service"
    INGRESS = "ingress"


class WorkloadStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class JobTargetType(str, enum.Enum):
    NODE = "node"
    SERVICE = "service"
    CONTAINER = "container"
    WORKLOAD = "workload"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class HealthCheckTargetType(str, enum.Enum):
    NODE = "node"
    SERVICE = "service"


class HealthCheckStatus(str, enum.Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


class ActivitySeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ActivityEventType(str, enum.Enum):
    NODE_ADDED = "node_added"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"
    HEALTH_CHECK_EXECUTED = "health_check_executed"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    SERVICE_STATUS_CHANGED = "service_status_changed"
    CONTAINER_STATUS_CHANGED = "container_status_changed"
    WORKLOAD_STATUS_CHANGED = "workload_status_changed"
