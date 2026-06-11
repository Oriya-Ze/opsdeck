export interface Node {
  id: string
  name: string
  hostname: string
  ip_address: string
  ssh_port: number
  ssh_user: string | null
  os_name: string
  environment: string
  role: string
  status: string
  cpu_usage: number
  ram_usage: number
  disk_usage: number
  uptime: string
  auto_sync_containers: boolean
  last_checked_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Service {
  id: string
  name: string
  description: string | null
  url: string | null
  node_id: string
  port: number | null
  protocol: string
  status: string
  category: string
  last_checked_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Container {
  id: string
  name: string
  image: string
  node_id: string
  status: string
  ports: string | null
  restart_count: number
  cpu_usage: number
  memory_usage: number
  created_at: string
  updated_at: string
}

export interface Workload {
  id: string
  name: string
  namespace: string
  kind: string
  cluster_name: string
  node_id: string | null
  replicas: number
  ready_replicas: number
  status: string
  image: string | null
  created_at: string
  updated_at: string
}

export interface JobAction {
  name: string
  label: string
  description: string
  requires_sudo: boolean
  timeout_seconds: number
  runner: string
  source: string
  is_editable: boolean
  custom_id: string | null
}

export interface CustomPlaybook {
  id: string
  name: string
  label: string
  description: string | null
  playbook_content: string
  requires_sudo: boolean
  timeout_seconds: number
  created_at: string
  updated_at: string
}

export interface CustomPlaybookCreate {
  name: string
  label: string
  description?: string
  playbook_content: string
  requires_sudo: boolean
  timeout_seconds: number
}

export interface Job {
  id: string
  job_id: string
  action_name: string
  target_type: string
  target_id: string
  target_name: string | null
  status: string
  started_at: string | null
  finished_at: string | null
  created_by: string
  output_log: string | null
  error_log: string | null
  created_at: string
}

export interface HealthCheck {
  id: string
  target_type: string
  target_id: string
  status: string
  response_time_ms: number | null
  message: string
  checked_at: string
}

export interface ActivityLog {
  id: string
  timestamp: string
  event_type: string
  message: string
  severity: string
  related_entity_type: string | null
  related_entity_id: string | null
}

export interface DashboardStats {
  total_nodes: number
  healthy_nodes: number
  warning_nodes: number
  offline_nodes: number
  running_services: number
  failed_services: number
  recent_jobs: Job[]
  last_health_check_at: string | null
}

export type NodeCreate = Omit<Node, 'id' | 'last_checked_at' | 'created_at' | 'updated_at'>
export type NodeUpdate = Partial<NodeCreate>
export type ServiceCreate = Omit<Service, 'id' | 'last_checked_at' | 'created_at' | 'updated_at'>
export type ServiceUpdate = Partial<ServiceCreate>
export type ContainerCreate = Omit<Container, 'id' | 'created_at' | 'updated_at'>
export type ContainerUpdate = Partial<ContainerCreate>
export type WorkloadCreate = Omit<Workload, 'id' | 'created_at' | 'updated_at'>
export type WorkloadUpdate = Partial<WorkloadCreate>

export interface SyncSettings {
  containers_auto_sync_enabled: boolean
  containers_sync_interval_seconds: number
  last_auto_sync_at: string | null
  last_auto_sync_summary: string | null
  updated_at: string | null
}

export interface PrometheusTarget {
  targets: string[]
  labels: Record<string, string>
}

export interface MonitoringStatus {
  prometheus_url: string
  grafana_url: string
  grafana_embed_url: string
  node_exporter_port: number
  targets_count: number
  targets: PrometheusTarget[]
  targets_file: string
  targets_updated_at: string | null
}

export interface MonitoringOverview {
  healthy_nodes: number | null
  running_containers: number | null
  up_services: number | null
  scrape_targets: number | null
  sync_runs_hour: number | null
  api_request_rate: number | null
  node_exporters_up: number | null
  node_exporters_total: number | null
  prometheus_reachable: boolean
  prometheus_error: string | null
}

export interface ScrapeTargetStatus {
  job: string
  instance: string
  health: string
  scrape_url: string
  last_scrape: string | null
  last_error: string | null
}

export interface ScrapeTargetsResponse {
  targets: ScrapeTargetStatus[]
  up: number
  down: number
  unknown: number
}

export interface PrometheusSeriesPoint {
  timestamp: number
  value: number
}

export interface PrometheusSeries {
  metric: Record<string, string>
  points: PrometheusSeriesPoint[]
}

export interface PrometheusQueryRangeResponse {
  query: string
  series: PrometheusSeries[]
}

export interface NodePrometheusSyncResponse {
  nodes_attempted: number
  nodes_synced: number
  nodes_skipped: number
  nodes_failed: number
  summary: string
  errors: string[]
}

export interface AutoSyncRunResponse {
  nodes_attempted: number
  nodes_succeeded: number
  nodes_failed: number
  total_containers: number
  summary: string
  errors: string[]
}

export interface SshSettings {
  configured: boolean
  ssh_user: string | null
  key_fingerprint: string | null
  public_key: string | null
  updated_at: string | null
}

export interface SshSettingsSave {
  ssh_user: string
  private_key?: string
  public_key?: string | null
}

export interface SshTestRequest {
  host: string
  port?: number
  ssh_user?: string | null
  private_key?: string | null
}

export interface SshTestResponse {
  success: boolean
  message: string
  response_time_ms: number | null
  output: string | null
}

export interface SshGenerateResponse {
  public_key: string
  private_key: string
  fingerprint: string
  instructions: string
}

export interface NodeTestConnectionResponse {
  success: boolean
  message: string
  response_time_ms: number | null
  output: string | null
}

export interface ContainerSyncResponse {
  node_id: string
  node_name: string
  synced: number
  removed: number
  containers: Container[]
}

export interface WorkloadSyncResponse {
  node_id: string
  node_name: string
  synced: number
  removed: number
  workloads: Workload[]
}
