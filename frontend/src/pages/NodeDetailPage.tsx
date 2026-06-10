import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Box, Container, HeartPulse, Package, Plug, RefreshCw, HardDrive, Database } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatusBadge } from '../components/StatusBadge'
import { UsageBar } from '../components/UsageBar'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { formatDate, formatRelative } from '../utils/format'

const ACTIONS = [
  { name: 'health-check', label: 'Run Health Check', icon: HeartPulse },
  { name: 'update-packages', label: 'Update Packages', icon: Package },
  { name: 'restart-docker', label: 'Restart Docker', icon: RefreshCw },
  { name: 'install-node-exporter', label: 'Install Node Exporter', icon: Database },
  { name: 'run-backup', label: 'Run Backup', icon: HardDrive },
]

export function NodeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: node, loading, error, refetch } = useFetch(() => api.getNode(id!), [id])
  const { data: services } = useFetch(() => api.getServices())
  const { data: healthChecks, refetch: refetchHC } = useFetch(
    () => api.getHealthChecks({ target_type: 'node', target_id: id!, limit: 10 }),
    [id],
  )
  const { data: jobs } = useFetch(() => api.getJobs())
  const { data: containers, loading: containersLoading, refetch: refetchContainers } = useFetch(
    () => api.getContainers(id!),
    [id],
  )
  const { data: workloads, loading: workloadsLoading, refetch: refetchWorkloads } = useFetch(
    () => api.getWorkloads(id!),
    [id],
  )
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [testingConn, setTestingConn] = useState(false)
  const [syncingContainers, setSyncingContainers] = useState(false)
  const [syncingWorkloads, setSyncingWorkloads] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)
  const [workloadSyncResult, setWorkloadSyncResult] = useState<string | null>(null)
  const [connResult, setConnResult] = useState<{ success: boolean; message: string } | null>(null)

  const nodeServices = services?.filter((s) => s.node_id === id) || []
  const nodeJobs = jobs?.filter((j) => j.target_id === id).slice(0, 5) || []

  const testConnection = async () => {
    setTestingConn(true)
    setConnResult(null)
    try {
      const result = await api.testNodeConnection(id!)
      setConnResult({ success: result.success, message: result.message })
    } catch (err) {
      setConnResult({ success: false, message: err instanceof Error ? err.message : 'Test failed' })
    } finally {
      setTestingConn(false)
    }
  }

  const syncContainers = async () => {
    setSyncingContainers(true)
    setSyncResult(null)
    try {
      const result = await api.syncNodeContainers(id!)
      setSyncResult(`Synced ${result.synced} container(s)${result.removed ? `, removed ${result.removed}` : ''}`)
      refetchContainers()
    } catch (err) {
      setSyncResult(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncingContainers(false)
    }
  }

  const syncWorkloads = async () => {
    setSyncingWorkloads(true)
    setWorkloadSyncResult(null)
    try {
      const result = await api.syncNodeWorkloads(id!)
      setWorkloadSyncResult(
        `Synced ${result.synced} workload(s)${result.removed ? `, removed ${result.removed}` : ''}`,
      )
      refetchWorkloads()
    } catch (err) {
      setWorkloadSyncResult(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncingWorkloads(false)
    }
  }

  const runAction = async (action: string) => {
    setActionLoading(action)
    try {
      await api.runNodeAction(id!, action)
      refetch()
      refetchHC()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error || !node) {
    return (
      <div>
        <Link to="/nodes" className="text-accent flex items-center gap-2 mb-4">
          <ArrowLeft size={16} /> Back to Nodes
        </Link>
        <div className="card text-red-400">{error || 'Node not found'}</div>
      </div>
    )
  }

  return (
    <div>
      <Link to="/nodes" className="text-accent flex items-center gap-2 mb-4 text-sm hover:underline">
        <ArrowLeft size={16} /> Back to Nodes
      </Link>

      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{node.name}</h1>
            <StatusBadge status={node.status} />
          </div>
          <p className="text-gray-400 mt-1">{node.hostname} · {node.ip_address}:{node.ssh_port}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-secondary flex items-center gap-2 text-xs"
            onClick={testConnection}
            disabled={testingConn}
          >
            <Plug size={14} />
            {testingConn ? 'Testing...' : 'Test SSH'}
          </button>
          {ACTIONS.map(({ name, label, icon: Icon }) => (
            <button
              key={name}
              className="btn-secondary flex items-center gap-2 text-xs"
              onClick={() => runAction(name)}
              disabled={actionLoading !== null}
            >
              <Icon size={14} />
              {actionLoading === name ? 'Running...' : label}
            </button>
          ))}
        </div>
      </div>

      {connResult && (
        <div className={`card mb-4 text-sm ${connResult.success ? 'text-emerald-400 border-emerald-500/30' : 'text-red-400 border-red-500/30'}`}>
          {connResult.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="card lg:col-span-1">
          <h2 className="text-lg font-semibold text-white mb-4">Basic Information</h2>
          <dl className="space-y-3 text-sm">
            {[
              ['OS', node.os_name],
              ['SSH User', node.ssh_user || 'global default'],
              ['Environment', node.environment],
              ['Role', node.role.replace(/-/g, ' ')],
              ['Uptime', node.uptime],
              ['Last Checked', formatRelative(node.last_checked_at)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between">
                <dt className="text-gray-400">{label}</dt>
                <dd className="text-gray-200 capitalize">{value}</dd>
              </div>
            ))}
          </dl>
          {node.notes && (
            <p className="mt-4 text-sm text-gray-400 border-t border-border pt-4">{node.notes}</p>
          )}
        </div>

        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Resource Usage</h2>
          <div className="space-y-4">
            <UsageBar label="CPU" value={node.cpu_usage} />
            <UsageBar label="RAM" value={node.ram_usage} />
            <UsageBar label="Disk" value={node.disk_usage} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Services on this Node</h2>
          {nodeServices.length === 0 ? (
            <p className="text-gray-500 text-sm">No services deployed on this node</p>
          ) : (
            <div className="space-y-2">
              {nodeServices.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <span className="text-gray-200">{s.name}</span>
                  <StatusBadge status={s.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Docker Containers</h2>
            <button
              className="btn-secondary flex items-center gap-2 text-xs py-1 px-2"
              onClick={syncContainers}
              disabled={syncingContainers}
            >
              <Container size={14} />
              {syncingContainers ? 'Syncing...' : 'Sync Containers'}
            </button>
          </div>
          {syncResult && (
            <p className={`text-xs mb-3 ${syncResult.includes('failed') || syncResult.includes('not') ? 'text-red-400' : 'text-emerald-400'}`}>
              {syncResult}
            </p>
          )}
          {containersLoading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : !containers || containers.length === 0 ? (
            <p className="text-gray-500 text-sm">No containers synced. Click Sync to pull live data from Docker.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="table-header">Name</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Image</th>
                    <th className="table-header">CPU</th>
                    <th className="table-header">Memory</th>
                  </tr>
                </thead>
                <tbody>
                  {containers.map((c) => (
                    <tr key={c.id} className="border-b border-border/50">
                      <td className="table-cell font-medium text-white">{c.name}</td>
                      <td className="table-cell"><StatusBadge status={c.status} /></td>
                      <td className="table-cell font-mono text-xs text-gray-400 max-w-[140px] truncate">{c.image}</td>
                      <td className="table-cell font-mono text-sm">{c.cpu_usage.toFixed(1)}%</td>
                      <td className="table-cell font-mono text-sm">{c.memory_usage.toFixed(0)} MB</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Kubernetes Workloads</h2>
            <button
              className="btn-secondary flex items-center gap-2 text-xs py-1 px-2"
              onClick={syncWorkloads}
              disabled={syncingWorkloads}
            >
              <Box size={14} />
              {syncingWorkloads ? 'Syncing...' : 'Sync Workloads'}
            </button>
          </div>
          {workloadSyncResult && (
            <p className={`text-xs mb-3 ${workloadSyncResult.includes('failed') || workloadSyncResult.includes('not') ? 'text-red-400' : 'text-emerald-400'}`}>
              {workloadSyncResult}
            </p>
          )}
          {workloadsLoading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : !workloads || workloads.length === 0 ? (
            <p className="text-gray-500 text-sm">No workloads synced. Click Sync to pull live data from Kubernetes.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="table-header">Name</th>
                    <th className="table-header">Namespace</th>
                    <th className="table-header">Kind</th>
                    <th className="table-header">Replicas</th>
                    <th className="table-header">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {workloads.map((w) => (
                    <tr key={w.id} className="border-b border-border/50">
                      <td className="table-cell font-medium text-white">{w.name}</td>
                      <td className="table-cell font-mono text-sm">{w.namespace}</td>
                      <td className="table-cell capitalize">{w.kind}</td>
                      <td className="table-cell font-mono text-sm">{w.ready_replicas}/{w.replicas}</td>
                      <td className="table-cell"><StatusBadge status={w.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Jobs</h2>
          {nodeJobs.length === 0 ? (
            <p className="text-gray-500 text-sm">No jobs for this node</p>
          ) : (
            <div className="space-y-2">
              {nodeJobs.map((j) => (
                <div key={j.id} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <div>
                    <span className="font-mono text-sm text-accent">{j.job_id}</span>
                    <span className="text-gray-500 text-sm ml-2 capitalize">{j.action_name.replace(/-/g, ' ')}</span>
                  </div>
                  <StatusBadge status={j.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Health Checks</h2>
          {!healthChecks || healthChecks.length === 0 ? (
            <p className="text-gray-500 text-sm">No health checks recorded</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="table-header">Status</th>
                    <th className="table-header">Response</th>
                    <th className="table-header">Message</th>
                    <th className="table-header">Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {healthChecks.map((hc) => (
                    <tr key={hc.id} className="border-b border-border/50">
                      <td className="table-cell"><StatusBadge status={hc.status} /></td>
                      <td className="table-cell font-mono">{hc.response_time_ms ? `${hc.response_time_ms}ms` : '—'}</td>
                      <td className="table-cell text-gray-400">{hc.message}</td>
                      <td className="table-cell text-gray-500">{formatDate(hc.checked_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
