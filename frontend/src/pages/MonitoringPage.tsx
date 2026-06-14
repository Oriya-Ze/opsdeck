import { useMemo, useState } from 'react'
import {
  Activity,
  CheckCircle,
  ExternalLink,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import type { PrometheusSeries } from '../types'
import { formatDate } from '../utils/format'

type Tab = 'charts' | 'targets' | 'grafana'

const CHART_COLORS = ['#38bdf8', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb7185']

function seriesToChartData(series: PrometheusSeries[]) {
  const byTime = new Map<number, Record<string, number | string>>()
  for (const item of series) {
    const label =
      item.metric.instance ||
      item.metric.node ||
      item.metric.status ||
      Object.values(item.metric).join(' ') ||
      'value'
    for (const point of item.points) {
      const time = point.timestamp * 1000
      const row = byTime.get(time) || { time }
      row[label] = point.value
      byTime.set(time, row)
    }
  }
  return Array.from(byTime.values()).sort((a, b) => (a.time as number) - (b.time as number))
}

function formatChartTime(value: number) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function MetricChart({
  title,
  series,
  loading,
  valueFormatter,
}: {
  title: string
  series: PrometheusSeries[]
  loading: boolean
  valueFormatter?: (value: number) => string
}) {
  const data = useMemo(() => seriesToChartData(series), [series])
  const keys = useMemo(() => {
    if (data.length === 0) return []
    return Object.keys(data[0]).filter((k) => k !== 'time')
  }, [data])

  return (
    <div className="card">
      <h3 className="font-semibold text-white mb-4">{title}</h3>
      {loading ? (
        <div className="h-64 flex items-center justify-center text-gray-500">Loading chart...</div>
      ) : data.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-gray-500">No data yet</div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsLineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
              <XAxis dataKey="time" tickFormatter={formatChartTime} stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} />
              <Tooltip
                labelFormatter={(value) => formatChartTime(Number(value))}
                formatter={(value: number) =>
                  valueFormatter ? valueFormatter(value) : value.toFixed(2)
                }
                contentStyle={{ background: '#1a1f2b', border: '1px solid #2a2f3a' }}
              />
              <Legend />
              {keys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={CHART_COLORS[index % CHART_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                />
              ))}
            </RechartsLineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export function MonitoringPage() {
  const [tab, setTab] = useState<Tab>('grafana')
  const [refreshing, setRefreshing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  const { data: status } = useFetch(() => api.getMonitoringStatus(), [], { pollIntervalMs: 60_000 })
  const { data: overview, refetch: refetchOverview } = useFetch(
    () => api.getMonitoringOverview(),
    [],
    { pollIntervalMs: 30_000 },
  )
  const { data: scrapeTargets, loading: targetsLoading, refetch: refetchTargets } = useFetch(
    () => api.getPrometheusTargets(),
    [],
    { pollIntervalMs: 30_000 },
  )
  const { data: apiChart, loading: apiChartLoading } = useFetch(
    () => api.getPrometheusQueryRange('sum(rate(opsdeck_http_requests_total[5m]))', 6),
    [],
    { pollIntervalMs: 60_000 },
  )
  const { data: cpuChart, loading: cpuChartLoading } = useFetch(
    () =>
      api.getPrometheusQueryRange(
        '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        6,
      ),
    [],
    { pollIntervalMs: 60_000 },
  )

  const handleRefresh = async () => {
    setRefreshing(true)
    setSyncMsg(null)
    try {
      const [nodeSync] = await Promise.all([
        api.syncNodesFromPrometheus(),
        api.refreshMonitoringTargets(),
        refetchOverview(),
        refetchTargets(),
      ])
      setSyncMsg(nodeSync.summary)
    } catch (err) {
      setSyncMsg(err instanceof Error ? err.message : 'Refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'grafana', label: 'Grafana Dashboard' },
    { id: 'charts', label: 'Live Charts' },
    { id: 'targets', label: 'Prometheus Targets' },
  ]

  return (
    <div>
      <PageHeader
        title="Monitoring"
        description="Time-series metrics, scrape health, and Grafana dashboards"
        actions={
          <div className="flex gap-2">
            <button className="btn-secondary flex items-center gap-2" onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
            {status?.prometheus_url ? (
              <a
                href={status.prometheus_url}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary flex items-center gap-2"
              >
                <ExternalLink size={14} /> Prometheus
              </a>
            ) : null}
            {status?.grafana_url ? (
              <a
                href={status.grafana_url}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary flex items-center gap-2"
              >
                <ExternalLink size={14} /> Grafana
              </a>
            ) : null}
          </div>
        }
      />

      {!overview?.prometheus_reachable && (
        <div className="card text-amber-400 mb-4">
          Prometheus is unreachable from OpsDeck backend.
          {overview?.prometheus_error && (
            <span className="block text-sm text-gray-400 mt-1">{overview.prometheus_error}</span>
          )}
        </div>
      )}

      {syncMsg && (
        <p className={`text-sm mb-4 ${syncMsg.includes('failed') ? 'text-red-400' : 'text-emerald-400'}`}>
          {syncMsg}
        </p>
      )}

      <div className="flex gap-2 mb-6">
        {tabs.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'grafana' && (
        <div className="card p-0 overflow-hidden">
          {status?.grafana_embed_url ? (
            <iframe
              title="OpsDeck Grafana Dashboard"
              src={status.grafana_embed_url}
              className="w-full border-0"
              style={{ height: '720px' }}
            />
          ) : (
            <div className="p-8 text-center text-gray-500">
              Grafana embed URL is not configured. Set GRAFANA_EMBED_URL in the backend environment.
            </div>
          )}
        </div>
      )}

      {tab === 'charts' && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <StatCard
              title="Node Exporters Up"
              value={
                overview?.node_exporters_total != null
                  ? `${overview?.node_exporters_up ?? 0}/${overview.node_exporters_total}`
                  : '—'
              }
              icon={Activity}
              subtitle="Install via Jobs on each node"
            />
            <StatCard
              title="Scrape Targets Up"
              value={scrapeTargets ? `${scrapeTargets.up}/${scrapeTargets.targets.length}` : '—'}
              icon={scrapeTargets?.down ? XCircle : CheckCircle}
              color={scrapeTargets?.down ? 'text-amber-400' : 'text-emerald-400'}
            />
            <StatCard
              title="Sync Runs (1h)"
              value={overview?.sync_runs_hour != null ? Math.round(overview.sync_runs_hour) : '—'}
              icon={RefreshCw}
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <MetricChart
              title="OpsDeck API Request Rate"
              series={apiChart?.series || []}
              loading={apiChartLoading}
              valueFormatter={(v) => `${v.toFixed(3)} req/s`}
            />
            <MetricChart
              title="Node CPU Usage (node_exporter)"
              series={cpuChart?.series || []}
              loading={cpuChartLoading}
              valueFormatter={(v) => `${v.toFixed(1)}%`}
            />
          </div>
        </>
      )}

      {tab === 'targets' && (
        <div className="card overflow-x-auto p-0">
          {targetsLoading && !scrapeTargets ? (
            <div className="p-6"><LoadingSpinner /></div>
          ) : (
            <>
              <div className="px-4 py-3 border-b border-border flex gap-4 text-sm">
                <span className="text-emerald-400">{scrapeTargets?.up ?? 0} up</span>
                <span className="text-red-400">{scrapeTargets?.down ?? 0} down</span>
                <span className="text-gray-500">{scrapeTargets?.unknown ?? 0} unknown</span>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="table-header">Job</th>
                    <th className="table-header">Instance</th>
                    <th className="table-header">Health</th>
                    <th className="table-header">Scrape URL</th>
                    <th className="table-header">Last Scrape</th>
                    <th className="table-header">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {(scrapeTargets?.targets || []).map((target) => (
                    <tr key={`${target.job}-${target.instance}-${target.scrape_url}`} className="border-b border-border/50">
                      <td className="table-cell">{target.job}</td>
                      <td className="table-cell font-medium">{target.instance || '—'}</td>
                      <td className="table-cell">
                        <StatusBadge
                          status={
                            target.health === 'up' ? 'healthy' : target.health === 'down' ? 'offline' : 'unknown'
                          }
                        />
                      </td>
                      <td className="table-cell font-mono text-xs text-gray-400">{target.scrape_url}</td>
                      <td className="table-cell text-gray-500 text-sm">
                        {target.last_scrape ? formatDate(target.last_scrape) : '—'}
                      </td>
                      <td className="table-cell text-red-400 text-xs max-w-xs truncate">
                        {target.last_error || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  )
}
