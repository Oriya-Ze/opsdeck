import { useState } from 'react'
import { FileCode, Plus } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import type { CustomPlaybook, CustomPlaybookCreate } from '../types'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { Modal } from '../components/Modal'
import { EmptyState } from '../components/EmptyState'

const DEFAULT_PLAYBOOK = `---
- hosts: all
  gather_facts: true
  tasks:
    - name: Hello from OpsDeck
      ansible.builtin.debug:
        msg: "Custom playbook executed successfully"
`

const defaultForm: CustomPlaybookCreate = {
  name: '',
  label: '',
  description: '',
  playbook_content: DEFAULT_PLAYBOOK,
  requires_sudo: false,
  timeout_seconds: 300,
}

export function PlaybooksPage() {
  const { data: playbooks, loading, error, refetch } = useFetch(() => api.getPlaybooks())
  const { data: builtinPlaybooks } = useFetch(() => api.getBuiltinPlaybooks())
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CustomPlaybook | null>(null)
  const [form, setForm] = useState<CustomPlaybookCreate>(defaultForm)
  const [saving, setSaving] = useState(false)

  const openCreate = () => {
    setEditing(null)
    setForm(defaultForm)
    setModalOpen(true)
  }

  const openEdit = (playbook: CustomPlaybook) => {
    setEditing(playbook)
    setForm({
      name: playbook.name,
      label: playbook.label,
      description: playbook.description || '',
      playbook_content: playbook.playbook_content,
      requires_sudo: playbook.requires_sudo,
      timeout_seconds: playbook.timeout_seconds,
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await api.updatePlaybook(editing.id, {
          label: form.label,
          description: form.description,
          playbook_content: form.playbook_content,
          requires_sudo: form.requires_sudo,
          timeout_seconds: form.timeout_seconds,
        })
      } else {
        await api.createPlaybook(form)
      }
      setModalOpen(false)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save playbook')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (playbook: CustomPlaybook) => {
    if (!confirm(`Delete playbook "${playbook.name}"?`)) return
    try {
      await api.deletePlaybook(playbook.id)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete playbook')
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Ansible Playbooks"
        description="Built-in automation playbooks and your custom playbooks for node actions"
        actions={
          <button className="btn-primary flex items-center gap-2" onClick={openCreate}>
            <Plus size={16} /> Add Playbook
          </button>
        }
      />

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Built-in Playbooks</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {builtinPlaybooks?.map((pb) => (
            <div key={pb.name} className="border border-border rounded-lg p-4 bg-surface/50">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-white">{pb.label}</p>
                  <p className="font-mono text-xs text-accent mt-1">{pb.name}</p>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-surface-overlay text-gray-400">built-in</span>
              </div>
              <p className="text-sm text-gray-400 mt-2">{pb.description}</p>
              <p className="text-xs text-gray-500 mt-2">
                {pb.requires_sudo ? 'Requires sudo' : 'No sudo'} · {pb.timeout_seconds}s timeout
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Custom Playbooks</h2>
        {!playbooks || playbooks.length === 0 ? (
          <EmptyState
            icon={FileCode}
            title="No custom playbooks"
            description="Add your own Ansible playbooks and run them as node actions from the node detail page."
            action={<button className="btn-primary" onClick={openCreate}>Add Playbook</button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="table-header">Name</th>
                  <th className="table-header">Label</th>
                  <th className="table-header">Sudo</th>
                  <th className="table-header">Timeout</th>
                  <th className="table-header">Updated</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {playbooks.map((pb) => (
                  <tr key={pb.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                    <td className="table-cell font-mono text-accent">{pb.name}</td>
                    <td className="table-cell">{pb.label}</td>
                    <td className="table-cell">{pb.requires_sudo ? 'Yes' : 'No'}</td>
                    <td className="table-cell font-mono text-sm">{pb.timeout_seconds}s</td>
                    <td className="table-cell text-gray-500 text-sm">
                      {new Date(pb.updated_at).toLocaleDateString()}
                    </td>
                    <td className="table-cell">
                      <div className="flex gap-2">
                        <button className="btn-secondary text-xs py-1 px-2" onClick={() => openEdit(pb)}>
                          Edit
                        </button>
                        <button className="btn-danger text-xs py-1 px-2" onClick={() => handleDelete(pb)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal
        title={editing ? `Edit Playbook: ${editing.name}` : 'Add Custom Playbook'}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        wide
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Action name (slug)</label>
              <input
                className="input font-mono"
                required
                disabled={!!editing}
                placeholder="my-playbook"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              {!editing && (
                <p className="text-xs text-gray-500 mt-1">Lowercase, numbers, hyphens. Used to run the action on nodes.</p>
              )}
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Display label</label>
              <input
                className="input"
                required
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-gray-400 mb-1">Description</label>
              <input
                className="input"
                value={form.description || ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Timeout (seconds)</label>
              <input
                className="input"
                type="number"
                min={30}
                max={3600}
                value={form.timeout_seconds}
                onChange={(e) => setForm({ ...form, timeout_seconds: +e.target.value })}
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={form.requires_sudo}
                  onChange={(e) => setForm({ ...form, requires_sudo: e.target.checked })}
                />
                Requires passwordless sudo
              </label>
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Playbook YAML</label>
            <textarea
              className="input font-mono text-xs h-64"
              required
              value={form.playbook_content}
              onChange={(e) => setForm({ ...form, playbook_content: e.target.value })}
            />
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
