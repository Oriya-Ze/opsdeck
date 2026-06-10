import { useMemo, useState } from 'react'
import { Box, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { EmptyState } from '../components/EmptyState'
import { formatRelative } from '../utils/format'

const KIND_OPTIONS = [
  { value: 'all', label: 'All kinds' },
  { value: 'deployment', label: 'Deployment' },
  { value: 'statefulset', label: 'StatefulSet' },
  { value: 'daemonset', label: 'DaemonSet' },
  { value: 'pod', label: 'Pod' },
  { value: 'service', label: 'Service' },
  { value: 'ingress', label: 'Ingress' },
]

export function KubernetesPage() {
  const { data: nodes } = useFetch(() => api.getNodes())
  const [nodeFilter, setNodeFilter] = useState('all')
  const { data: workloads, loading, error, refetch } = useFetch(
    () => api.getWorkloads(nodeFilter === 'all' ? undefined : nodeFilter),
    [nodeFilter],
  )
  const [search, setSearch] = useState('')
  const [namespaceFilter, setNamespaceFilter] = useState('all')
  const [kindFilter, setKindFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [syncNodeId, setSyncNodeId] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  const nodeMap = useMemo(() => {
    const m = new Map<string, string>()
    nodes?.forEach((n) => m.set(n.id, n.name))
    return m
  }, [nodes])

  const namespaces = useMemo(() => {
    if (!workloads) return []
    return [...new Set(workloads.map((w) => w.namespace))].sort()
  }, [workloads])

  const filtered = useMemo(() => {
    if (!workloads) return []
    return workloads.filter((w) => {
      const matchSearch = w.name.toLowerCase().includes(search.toLowerCase())
      const matchNs = namespaceFilter === 'all' || w.namespace === namespaceFilter
      const matchKind = kindFilter === 'all' || w.kind === kindFilter
      const matchStatus = statusFilter === 'all' || w.status === statusFilter
      return matchSearch && matchNs && matchKind && matchStatus
    })
  }, [workloads, search, namespaceFilter, kindFilter, statusFilter])

  const handleSync = async () => {
    if (!syncNodeId) {
      alert('Select a node to sync')
      return
    }
    setSyncing(true)
    setSyncMsg(null)
    try {
      const result = await api.syncNodeWorkloads(syncNodeId)
      setSyncMsg(
        `Synced ${result.synced} workload(s) from ${result.node_name}${
          result.removed ? `, removed ${result.removed}` : ''
        }`,
      )
      if (nodeFilter === 'all' || nodeFilter === syncNodeId) {
        refetch()
      } else {
        setNodeFilter(syncNodeId)
      }
    } catch (err) {
      setSyncMsg(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  if (loading && !workloads) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Kubernetes Workloads"
        description="Live K3s/Kubernetes workloads synced via SSH and kubectl"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search workloads..." />
        <select
          className="select sm:w-44"
          value={nodeFilter}
          onChange={(e) => setNodeFilter(e.target.value)}
        >
          <option value="all">All nodes</option>
          {nodes?.map((n) => (
            <option key={n.id} value={n.id}>{n.name}</option>
          ))}
        </select>
        <select className="select sm:w-44" value={namespaceFilter} onChange={(e) => setNamespaceFilter(e.target.value)}>
          <option value="all">All namespaces</option>
          {namespaces.map((ns) => (
            <option key={ns} value={ns}>{ns}</option>
          ))}
        </select>
        <select className="select sm:w-44" value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
          {KIND_OPTIONS.map((k) => (
            <option key={k.value} value={k.value}>{k.label}</option>
          ))}
        </select>
        <select className="select sm:w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="healthy">Healthy</option>
          <option value="degraded">Degraded</option>
          <option value="failed">Failed</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <select
          className="select sm:w-52"
          value={syncNodeId}
          onChange={(e) => setSyncNodeId(e.target.value)}
        >
          <option value="">Select node to sync...</option>
          {nodes?.map((n) => (
            <option key={n.id} value={n.id}>{n.name}</option>
          ))}
        </select>
        <button
          className="btn-secondary flex items-center gap-2 whitespace-nowrap"
          onClick={handleSync}
          disabled={syncing || !syncNodeId}
        >
          <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing...' : 'Sync from Kubernetes'}
        </button>
      </div>

      {syncMsg && (
        <div className={`card text-sm mb-4 py-3 ${syncMsg.includes('failed') || syncMsg.includes('not') ? 'text-red-400' : 'text-gray-300'}`}>
          {syncMsg}
        </div>
      )}

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Box}
          title="No workloads found"
          description="Select a K3s/Kubernetes node and click Sync to pull live deployments, pods, services, and more."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Name</th>
                <th className="table-header">Namespace</th>
                <th className="table-header">Kind</th>
                <th className="table-header">Node</th>
                <th className="table-header">Cluster</th>
                <th className="table-header">Replicas</th>
                <th className="table-header">Status</th>
                <th className="table-header">Image</th>
                <th className="table-header">Updated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((w) => (
                <tr key={w.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell font-medium text-white">{w.name}</td>
                  <td className="table-cell font-mono text-sm">{w.namespace}</td>
                  <td className="table-cell capitalize">{w.kind}</td>
                  <td className="table-cell">{w.node_id ? nodeMap.get(w.node_id) || '—' : '—'}</td>
                  <td className="table-cell">{w.cluster_name}</td>
                  <td className="table-cell font-mono">{w.ready_replicas}/{w.replicas}</td>
                  <td className="table-cell"><StatusBadge status={w.status} /></td>
                  <td className="table-cell font-mono text-xs text-gray-400 max-w-[180px] truncate">{w.image || '—'}</td>
                  <td className="table-cell text-gray-500">{formatRelative(w.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
