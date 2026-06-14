import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Server } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import type { Node, NodeCreate } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { Modal } from '../components/Modal'
import { EmptyState } from '../components/EmptyState'
import { formatRelative } from '../utils/format'

const defaultNode: NodeCreate = {
  name: '',
  hostname: '',
  ip_address: '',
  ssh_port: 22,
  ssh_user: null,
  os_name: 'Ubuntu 24.04 LTS',
  environment: 'local',
  role: 'server',
  status: 'unknown',
  cpu_usage: 0,
  ram_usage: 0,
  disk_usage: 0,
  uptime: 'unknown',
  auto_sync_containers: true,
  auto_backup_enabled: false,
  notes: '',
}

export function NodesPage() {
  const { data: nodes, loading, error, refetch } = useFetch(() => api.getNodes())
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Node | null>(null)
  const [form, setForm] = useState<NodeCreate>(defaultNode)
  const [saving, setSaving] = useState(false)

  const filtered = useMemo(() => {
    if (!nodes) return []
    return nodes.filter((n) => {
      const matchSearch =
        n.name.toLowerCase().includes(search.toLowerCase()) ||
        n.ip_address.includes(search) ||
        n.hostname.toLowerCase().includes(search.toLowerCase())
      const matchStatus = statusFilter === 'all' || n.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [nodes, search, statusFilter])

  const openCreate = () => {
    setEditing(null)
    setForm(defaultNode)
    setModalOpen(true)
  }

  const openEdit = (node: Node) => {
    setEditing(node)
    setForm({
      name: node.name,
      hostname: node.hostname,
      ip_address: node.ip_address,
      ssh_port: node.ssh_port,
      ssh_user: node.ssh_user,
      os_name: node.os_name,
      environment: node.environment,
      role: node.role,
      status: node.status,
      cpu_usage: node.cpu_usage,
      ram_usage: node.ram_usage,
      disk_usage: node.disk_usage,
      uptime: node.uptime,
      auto_sync_containers: node.auto_sync_containers,
      auto_backup_enabled: node.auto_backup_enabled,
      notes: node.notes || '',
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await api.updateNode(editing.id, form)
      } else {
        await api.createNode(form)
      }
      setModalOpen(false)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (node: Node) => {
    if (!confirm(`Delete node "${node.name}"?`)) return
    try {
      await api.deleteNode(node.id)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Nodes"
        description="Manage Linux nodes in your HomeLab"
        actions={
          <button className="btn-primary flex items-center gap-2" onClick={openCreate}>
            <Plus size={16} /> Add Node
          </button>
        }
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search nodes..." />
        <select className="select sm:w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="healthy">Healthy</option>
          <option value="warning">Warning</option>
          <option value="offline">Offline</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Server}
          title="No nodes found"
          description="Add your first Linux node to start managing your HomeLab."
          action={<button className="btn-primary" onClick={openCreate}>Add Node</button>}
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Name</th>
                <th className="table-header">IP</th>
                <th className="table-header">OS</th>
                <th className="table-header">Role</th>
                <th className="table-header">Environment</th>
                <th className="table-header">Status</th>
                <th className="table-header">Last Check</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((node) => (
                <tr key={node.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell">
                    <Link to={`/nodes/${node.id}`} className="text-accent hover:underline font-medium">
                      {node.name}
                    </Link>
                  </td>
                  <td className="table-cell font-mono text-sm">{node.ip_address}</td>
                  <td className="table-cell">{node.os_name}</td>
                  <td className="table-cell capitalize">{node.role.replace(/-/g, ' ')}</td>
                  <td className="table-cell capitalize">{node.environment}</td>
                  <td className="table-cell"><StatusBadge status={node.status} /></td>
                  <td className="table-cell text-gray-500">{formatRelative(node.last_checked_at)}</td>
                  <td className="table-cell">
                    <div className="flex gap-2">
                      <button className="btn-secondary text-xs py-1 px-2" onClick={() => openEdit(node)}>Edit</button>
                      <button className="btn-danger text-xs py-1 px-2" onClick={() => handleDelete(node)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal title={editing ? 'Edit Node' : 'Add Node'} open={modalOpen} onClose={() => setModalOpen(false)} wide>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Hostname</label>
              <input className="input" required value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">IP Address</label>
              <input className="input" required value={form.ip_address} onChange={(e) => setForm({ ...form, ip_address: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">SSH Port</label>
              <input className="input" type="number" value={form.ssh_port} onChange={(e) => setForm({ ...form, ssh_port: +e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">SSH User (optional override)</label>
              <input className="input" value={form.ssh_user || ''} onChange={(e) => setForm({ ...form, ssh_user: e.target.value || null })} placeholder="Uses global user from Settings" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">OS</label>
              <input className="input" required value={form.os_name} onChange={(e) => setForm({ ...form, os_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Environment</label>
              <select className="select" value={form.environment} onChange={(e) => setForm({ ...form, environment: e.target.value })}>
                <option value="local">Local</option>
                <option value="lab">Lab</option>
                <option value="aws">AWS</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Role</label>
              <select className="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="master">Master</option>
                <option value="worker">Worker</option>
                <option value="vm">VM</option>
                <option value="raspberry-pi">Raspberry Pi</option>
                <option value="server">Server</option>
              </select>
            </div>
          </div>
          <div className="col-span-2">
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={form.auto_sync_containers}
                onChange={(e) => setForm({ ...form, auto_sync_containers: e.target.checked })}
              />
              Include in automatic Docker container sync
            </label>
          </div>
          <div className="col-span-2">
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={form.auto_backup_enabled}
                onChange={(e) => setForm({ ...form, auto_backup_enabled: e.target.checked })}
              />
              Include in automatic node backups (/etc, /home → local or S3)
            </label>
          </div>
          <div className="col-span-2">
            <label className="block text-sm text-gray-400 mb-1">Notes</label>
            <textarea className="input h-20" value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
