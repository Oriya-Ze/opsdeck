import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { HeartPulse, Layers, Plus } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import type { Service, ServiceCreate } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { Modal } from '../components/Modal'
import { EmptyState } from '../components/EmptyState'
import { formatRelative } from '../utils/format'

function isWebUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

const defaultService: ServiceCreate = {
  name: '',
  description: '',
  url: '',
  node_id: '',
  port: null,
  protocol: 'http',
  status: 'unknown',
  category: 'other',
  notes: '',
}

export function ServicesPage() {
  const { data: nodes } = useFetch(() => api.getNodes())
  const [nodeFilter, setNodeFilter] = useState('all')
  const { data: services, loading, error, refetch } = useFetch(
    () => api.getServices(nodeFilter === 'all' ? undefined : nodeFilter),
    [nodeFilter],
  )
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Service | null>(null)
  const [form, setForm] = useState<ServiceCreate>(defaultService)
  const [saving, setSaving] = useState(false)
  const [checkingId, setCheckingId] = useState<string | null>(null)
  const [checkingAll, setCheckingAll] = useState(false)
  const [checkAllSummary, setCheckAllSummary] = useState<string | null>(null)

  const nodeMap = useMemo(() => {
    const m = new Map<string, string>()
    nodes?.forEach((n) => m.set(n.id, n.name))
    return m
  }, [nodes])

  const filtered = useMemo(() => {
    if (!services) return []
    return services.filter((s) => {
      const matchSearch = s.name.toLowerCase().includes(search.toLowerCase())
      const matchCat = categoryFilter === 'all' || s.category === categoryFilter
      return matchSearch && matchCat
    })
  }, [services, search, categoryFilter])

  const openCreate = () => {
    setEditing(null)
    setForm({ ...defaultService, node_id: nodes?.[0]?.id || '' })
    setModalOpen(true)
  }

  const openEdit = (service: Service) => {
    setEditing(service)
    setForm({
      name: service.name,
      description: service.description || '',
      url: service.url || '',
      node_id: service.node_id,
      port: service.port,
      protocol: service.protocol,
      status: service.status,
      category: service.category,
      notes: service.notes || '',
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await api.updateService(editing.id, form)
      } else {
        await api.createService(form)
      }
      setModalOpen(false)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (service: Service) => {
    if (!confirm(`Delete service "${service.name}"?`)) return
    await api.deleteService(service.id)
    refetch()
  }

  const runHealthCheck = async (id: string) => {
    setCheckingId(id)
    setCheckAllSummary(null)
    try {
      await api.runServiceHealthCheck(id)
      refetch()
    } finally {
      setCheckingId(null)
    }
  }

  const runAllHealthChecks = async () => {
    if (!services?.length) return
    setCheckingAll(true)
    setCheckAllSummary(null)
    try {
      const results = await api.runAllServiceHealthChecks(
        nodeFilter === 'all' ? undefined : nodeFilter,
      )
      const counts = results.reduce(
        (acc, r) => {
          acc[r.status] = (acc[r.status] || 0) + 1
          return acc
        },
        {} as Record<string, number>,
      )
      const parts = [
        counts.success ? `${counts.success} up` : null,
        counts.warning ? `${counts.warning} warning` : null,
        counts.failed ? `${counts.failed} down` : null,
      ].filter(Boolean)
      setCheckAllSummary(`Checked ${results.length} services: ${parts.join(', ')}`)
      refetch()
    } catch (err) {
      setCheckAllSummary(err instanceof Error ? err.message : 'Check all failed')
    } finally {
      setCheckingAll(false)
    }
  }

  if (loading && !services) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Services"
        description="Manage HomeLab services and endpoints"
        actions={
          <button className="btn-primary flex items-center gap-2" onClick={openCreate}>
            <Plus size={16} /> Add Service
          </button>
        }
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search services..." />
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
        <select className="select sm:w-44" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
          <option value="all">All categories</option>
          <option value="monitoring">Monitoring</option>
          <option value="database">Database</option>
          <option value="proxy">Proxy</option>
          <option value="storage">Storage</option>
          <option value="ci-cd">CI/CD</option>
          <option value="gitops">GitOps</option>
          <option value="app">App</option>
          <option value="other">Other</option>
        </select>
        <button
          className="btn-secondary flex items-center gap-2 whitespace-nowrap"
          onClick={runAllHealthChecks}
          disabled={checkingAll || !services?.length}
        >
          <HeartPulse size={16} className={checkingAll ? 'animate-pulse' : ''} />
          {checkingAll ? 'Checking...' : 'Check All'}
        </button>
      </div>

      {checkAllSummary && (
        <div className="card text-sm text-gray-300 mb-4 py-3">{checkAllSummary}</div>
      )}

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No services found"
          description="Add services like Grafana, Prometheus, or Portainer to track your stack."
          action={<button className="btn-primary" onClick={openCreate}>Add Service</button>}
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Name</th>
                <th className="table-header">Node</th>
                <th className="table-header">URL</th>
                <th className="table-header">Category</th>
                <th className="table-header">Status</th>
                <th className="table-header">Last Check</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const nodeName = nodeMap.get(s.node_id)
                return (
                <tr key={s.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell font-medium text-white">{s.name}</td>
                  <td className="table-cell">
                    {nodeName ? (
                      <Link
                        to={`/nodes/${s.node_id}`}
                        className="text-accent hover:underline font-medium"
                      >
                        {nodeName}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="table-cell">
                    {s.url ? (
                      isWebUrl(s.url) ? (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-sm text-accent hover:underline"
                        >
                          {s.url}
                        </a>
                      ) : (
                        <span className="font-mono text-sm text-gray-400">{s.url}</span>
                      )
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="table-cell capitalize">{s.category.replace(/-/g, '/')}</td>
                  <td className="table-cell"><StatusBadge status={s.status} /></td>
                  <td className="table-cell text-gray-500">{formatRelative(s.last_checked_at)}</td>
                  <td className="table-cell">
                    <div className="flex gap-2">
                      <button
                        className="btn-secondary text-xs py-1 px-2 flex items-center gap-1"
                        onClick={() => runHealthCheck(s.id)}
                        disabled={checkingId === s.id || checkingAll}
                      >
                        <HeartPulse size={12} />
                        {checkingId === s.id ? '...' : 'Check'}
                      </button>
                      <button className="btn-secondary text-xs py-1 px-2" onClick={() => openEdit(s)}>Edit</button>
                      <button className="btn-danger text-xs py-1 px-2" onClick={() => handleDelete(s)}>Delete</button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      )}

      <Modal title={editing ? 'Edit Service' : 'Add Service'} open={modalOpen} onClose={() => setModalOpen(false)} wide>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Node</label>
              <select className="select" required value={form.node_id} onChange={(e) => setForm({ ...form, node_id: e.target.value })}>
                {nodes?.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-gray-400 mb-1">Description</label>
              <input className="input" value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">URL</label>
              <input className="input" value={form.url || ''} onChange={(e) => setForm({ ...form, url: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Port</label>
              <input className="input" type="number" value={form.port ?? ''} onChange={(e) => setForm({ ...form, port: e.target.value ? +e.target.value : null })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Protocol</label>
              <select className="select" value={form.protocol} onChange={(e) => setForm({ ...form, protocol: e.target.value })}>
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="tcp">TCP</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Category</label>
              <select className="select" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="monitoring">Monitoring</option>
                <option value="database">Database</option>
                <option value="proxy">Proxy</option>
                <option value="storage">Storage</option>
                <option value="ci-cd">CI/CD</option>
                <option value="gitops">GitOps</option>
                <option value="app">App</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving...' : editing ? 'Update' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
