import { useMemo, useState } from 'react'
import { Container, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { EmptyState } from '../components/EmptyState'
import { formatRelative } from '../utils/format'

export function ContainersPage() {
  const { data: containers, loading, error, refetch } = useFetch(() => api.getContainers())
  const { data: nodes } = useFetch(() => api.getNodes())
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [nodeFilter, setNodeFilter] = useState('all')
  const [syncNodeId, setSyncNodeId] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  const nodeMap = useMemo(() => {
    const m = new Map<string, string>()
    nodes?.forEach((n) => m.set(n.id, n.name))
    return m
  }, [nodes])

  const filtered = useMemo(() => {
    if (!containers) return []
    return containers.filter((c) => {
      const matchSearch =
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.image.toLowerCase().includes(search.toLowerCase())
      const matchStatus = statusFilter === 'all' || c.status === statusFilter
      const matchNode = nodeFilter === 'all' || c.node_id === nodeFilter
      return matchSearch && matchStatus && matchNode
    })
  }, [containers, search, statusFilter, nodeFilter])

  const handleSync = async () => {
    if (!syncNodeId) {
      alert('Select a node to sync')
      return
    }
    setSyncing(true)
    setSyncMsg(null)
    try {
      const result = await api.syncNodeContainers(syncNodeId)
      setSyncMsg(`Synced ${result.synced} container(s) from ${result.node_name}`)
      refetch()
    } catch (err) {
      setSyncMsg(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Docker Containers"
        description="Live Docker containers synced via SSH from your nodes"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Search containers..." />
        <select className="select sm:w-44" value={nodeFilter} onChange={(e) => setNodeFilter(e.target.value)}>
          <option value="all">All nodes</option>
          {nodes?.map((n) => (
            <option key={n.id} value={n.id}>{n.name}</option>
          ))}
        </select>
        <select className="select sm:w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="running">Running</option>
          <option value="stopped">Stopped</option>
          <option value="restarting">Restarting</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6 items-start sm:items-center">
        <select
          className="select sm:w-48"
          value={syncNodeId}
          onChange={(e) => setSyncNodeId(e.target.value)}
        >
          <option value="">Select node to sync...</option>
          {nodes?.map((n) => (
            <option key={n.id} value={n.id}>{n.name}</option>
          ))}
        </select>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleSync}
          disabled={syncing || !syncNodeId}
        >
          <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing...' : 'Sync from Docker'}
        </button>
        {syncMsg && (
          <span className={`text-sm ${syncMsg.includes('failed') || syncMsg.includes('not') ? 'text-red-400' : 'text-emerald-400'}`}>
            {syncMsg}
          </span>
        )}
      </div>

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Container}
          title="No containers found"
          description="Select a node and click Sync from Docker to pull live container data via SSH."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Name</th>
                <th className="table-header">Image</th>
                <th className="table-header">Node</th>
                <th className="table-header">Status</th>
                <th className="table-header">Ports</th>
                <th className="table-header">CPU</th>
                <th className="table-header">Memory</th>
                <th className="table-header">Restarts</th>
                <th className="table-header">Updated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell font-medium text-white">{c.name}</td>
                  <td className="table-cell font-mono text-xs text-gray-400 max-w-[200px] truncate">{c.image}</td>
                  <td className="table-cell">{nodeMap.get(c.node_id) || '—'}</td>
                  <td className="table-cell"><StatusBadge status={c.status} /></td>
                  <td className="table-cell font-mono text-xs">{c.ports || '—'}</td>
                  <td className="table-cell font-mono">{c.cpu_usage}%</td>
                  <td className="table-cell font-mono">{c.memory_usage} MB</td>
                  <td className="table-cell">{c.restart_count}</td>
                  <td className="table-cell text-gray-500">{formatRelative(c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
