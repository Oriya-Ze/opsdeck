import { useMemo, useState } from 'react'
import { Box } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { EmptyState } from '../components/EmptyState'
import { formatRelative } from '../utils/format'

export function KubernetesPage() {
  const { data: workloads, loading, error } = useFetch(() => api.getWorkloads())
  const [search, setSearch] = useState('')
  const [namespaceFilter, setNamespaceFilter] = useState('all')

  const namespaces = useMemo(() => {
    if (!workloads) return []
    return [...new Set(workloads.map((w) => w.namespace))]
  }, [workloads])

  const filtered = useMemo(() => {
    if (!workloads) return []
    return workloads.filter((w) => {
      const matchSearch = w.name.toLowerCase().includes(search.toLowerCase())
      const matchNs = namespaceFilter === 'all' || w.namespace === namespaceFilter
      return matchSearch && matchNs
    })
  }, [workloads, search, namespaceFilter])

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Kubernetes Workloads"
        description="K3s workloads and deployments (mock data)"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search workloads..." />
        <select className="select sm:w-44" value={namespaceFilter} onChange={(e) => setNamespaceFilter(e.target.value)}>
          <option value="all">All namespaces</option>
          {namespaces.map((ns) => (
            <option key={ns} value={ns}>{ns}</option>
          ))}
        </select>
      </div>

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Box}
          title="No workloads found"
          description="Kubernetes API integration will populate this view with live K3s workload data."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Name</th>
                <th className="table-header">Namespace</th>
                <th className="table-header">Kind</th>
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
