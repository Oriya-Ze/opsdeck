import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle, Container, Copy, Key, LineChart, RefreshCw, Shield, Trash2, Webhook } from 'lucide-react'
import { api } from '../api/client'
import { PageHeader } from '../components/PageHeader'
import type { SshGenerateResponse, SshSettings, SyncSettings } from '../types'
import { formatRelative } from '../utils/format'

const comingSoon = [
  { icon: Shield, title: 'Authentication', description: 'OAuth2, LDAP, or API key authentication (coming soon)' },
  { icon: Webhook, title: 'Webhooks & Notifications', description: 'Slack, Discord, and email alert integrations' },
]

export function SettingsPage() {
  const [sshSettings, setSshSettings] = useState<SshSettings | null>(null)
  const [sshUser, setSshUser] = useState('ubuntu')
  const [privateKey, setPrivateKey] = useState('')
  const [publicKey, setPublicKey] = useState('')
  const [testHost, setTestHost] = useState('')
  const [testPort, setTestPort] = useState(22)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [generated, setGenerated] = useState<SshGenerateResponse | null>(null)
  const [copied, setCopied] = useState(false)
  const [syncSettings, setSyncSettings] = useState<SyncSettings | null>(null)
  const [syncEnabled, setSyncEnabled] = useState(false)
  const [syncInterval, setSyncInterval] = useState(300)
  const [syncSaving, setSyncSaving] = useState(false)
  const [syncRunning, setSyncRunning] = useState(false)
  const [syncRunMsg, setSyncRunMsg] = useState<string | null>(null)
  const loadSettings = async () => {
    setLoading(true)
    try {
      const [sshData, syncData] = await Promise.all([api.getSshSettings(), api.getSyncSettings()])
      setSshSettings(sshData)
      if (sshData.ssh_user) setSshUser(sshData.ssh_user)
      setSyncSettings(syncData)
      setSyncEnabled(syncData.containers_auto_sync_enabled)
      setSyncInterval(syncData.containers_sync_interval_seconds)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!privateKey.trim() && !sshSettings?.configured) {
      alert('Please paste or generate a private key')
      return
    }
    setSaving(true)
    try {
      const saved = await api.saveSshSettings({
        ssh_user: sshUser,
        private_key: privateKey.trim() || undefined,
        public_key: publicKey || generated?.public_key || null,
      })
      setSshSettings(saved)
      setPrivateKey('')
      setGenerated(null)
      alert('SSH credentials saved successfully')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Remove saved SSH credentials?')) return
    try {
      await api.deleteSshSettings()
      setSshSettings({ configured: false, ssh_user: null, key_fingerprint: null, public_key: null, updated_at: null })
      setPrivateKey('')
      setPublicKey('')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const keys = await api.generateSshKey()
      setGenerated(keys)
      setPrivateKey(keys.private_key)
      setPublicKey(keys.public_key)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate key')
    } finally {
      setGenerating(false)
    }
  }

  const handleTest = async () => {
    if (!testHost) {
      alert('Enter a host IP to test')
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.testSshConnection({
        host: testHost,
        port: testPort,
        ssh_user: privateKey ? sshUser : undefined,
        private_key: privateKey || undefined,
      })
      setTestResult({ success: result.success, message: result.message })
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  const handleSaveSync = async (e: React.FormEvent) => {
    e.preventDefault()
    setSyncSaving(true)
    setSyncRunMsg(null)
    try {
      const saved = await api.saveSyncSettings({
        containers_auto_sync_enabled: syncEnabled,
        containers_sync_interval_seconds: syncInterval,
      })
      setSyncSettings(saved)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save sync settings')
    } finally {
      setSyncSaving(false)
    }
  }

  const handleRunSyncNow = async () => {
    setSyncRunning(true)
    setSyncRunMsg(null)
    try {
      const result = await api.runContainerAutoSync()
      setSyncRunMsg(result.summary)
      const refreshed = await api.getSyncSettings()
      setSyncSettings(refreshed)
    } catch (err) {
      setSyncRunMsg(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncRunning(false)
    }
  }

  const copyPublicKey = () => {
    const key = generated?.public_key || sshSettings?.public_key || publicKey
    if (key) {
      navigator.clipboard.writeText(key)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Configure SSH credentials and integrations"
      />

      {/* SSH Credentials */}
      <div className="card mb-6">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 rounded-lg bg-accent/15 text-accent">
            <Key size={22} />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white text-lg">SSH Credentials</h3>
            <p className="text-sm text-gray-400 mt-1">
              Global SSH key used for node health checks and automation jobs.
              Private keys are encrypted at rest.
            </p>
            {sshSettings?.configured && (
              <div className="mt-3 flex flex-wrap gap-3 text-sm">
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle size={14} /> Configured
                </span>
                <span className="text-gray-400">User: <span className="text-gray-200">{sshSettings.ssh_user}</span></span>
                <span className="text-gray-400 font-mono text-xs">FP: {sshSettings.key_fingerprint?.slice(0, 16)}...</span>
              </div>
            )}
          </div>
          {sshSettings?.configured && (
            <button className="btn-danger flex items-center gap-2 text-sm" onClick={handleDelete}>
              <Trash2 size={14} /> Remove
            </button>
          )}
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm">Loading...</p>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">SSH Username</label>
                <input
                  className="input"
                  required
                  value={sshUser}
                  onChange={(e) => setSshUser(e.target.value)}
                  placeholder="ubuntu"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  type="button"
                  className="btn-secondary flex items-center gap-2"
                  onClick={handleGenerate}
                  disabled={generating}
                >
                  <RefreshCw size={14} className={generating ? 'animate-spin' : ''} />
                  {generating ? 'Generating...' : 'Generate Key Pair'}
                </button>
              </div>
            </div>

            {(generated || sshSettings?.public_key || publicKey) && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Public Key (add to ~/.ssh/authorized_keys on target servers)</label>
                <div className="flex gap-2">
                  <textarea
                    className="input font-mono text-xs h-20 flex-1"
                    readOnly
                    value={generated?.public_key || publicKey || sshSettings?.public_key || ''}
                  />
                  <button type="button" className="btn-secondary px-3" onClick={copyPublicKey}>
                    {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
                  </button>
                </div>
                {generated && (
                  <p className="text-xs text-amber-400 mt-2">{generated.instructions}</p>
                )}
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Private Key {sshSettings?.configured && <span className="text-gray-500">(leave empty to keep existing)</span>}
              </label>
              <textarea
                className="input font-mono text-xs h-32"
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;..."
              />
              <p className="text-xs text-gray-500 mt-1">Paste an existing key or generate a new pair above.</p>
            </div>

            <div className="border-t border-border pt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Test Connection</h4>
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  className="input sm:flex-1"
                  placeholder="Host IP (e.g. 192.168.1.50)"
                  value={testHost}
                  onChange={(e) => setTestHost(e.target.value)}
                />
                <input
                  className="input w-full sm:w-24"
                  type="number"
                  placeholder="Port"
                  value={testPort}
                  onChange={(e) => setTestPort(+e.target.value)}
                />
                <button
                  type="button"
                  className="btn-secondary whitespace-nowrap"
                  onClick={handleTest}
                  disabled={testing}
                >
                  {testing ? 'Testing...' : 'Test SSH'}
                </button>
              </div>
              {testResult && (
                <p className={`text-sm mt-2 ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                  {testResult.message}
                </p>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving...' : sshSettings?.configured ? 'Update Credentials' : 'Save Credentials'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Container auto-sync */}
      <div className="card mb-6">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 rounded-lg bg-accent/15 text-accent">
            <Container size={22} />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white text-lg">Container Auto-Sync</h3>
            <p className="text-sm text-gray-400 mt-1">
              Periodically sync Docker containers from nodes with auto-sync enabled.
              Requires SSH credentials configured above.
            </p>
            {syncSettings?.last_auto_sync_at && (
              <p className="text-xs text-gray-500 mt-2">
                Last sync: {formatRelative(syncSettings.last_auto_sync_at)}
                {syncSettings.last_auto_sync_summary && (
                  <span className="text-gray-400"> — {syncSettings.last_auto_sync_summary}</span>
                )}
              </p>
            )}
          </div>
        </div>

        <form onSubmit={handleSaveSync} className="space-y-4">
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={syncEnabled}
              onChange={(e) => setSyncEnabled(e.target.checked)}
            />
            Enable automatic container sync
          </label>
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Sync interval</label>
              <select
                className="select sm:w-48"
                value={syncInterval}
                onChange={(e) => setSyncInterval(+e.target.value)}
              >
                <option value={60}>Every 1 minute</option>
                <option value={300}>Every 5 minutes</option>
                <option value={900}>Every 15 minutes</option>
                <option value={1800}>Every 30 minutes</option>
                <option value={3600}>Every 1 hour</option>
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={syncSaving}>
              {syncSaving ? 'Saving...' : 'Save Sync Settings'}
            </button>
            <button
              type="button"
              className="btn-secondary flex items-center gap-2"
              onClick={handleRunSyncNow}
              disabled={syncRunning}
            >
              <RefreshCw size={14} className={syncRunning ? 'animate-spin' : ''} />
              {syncRunning ? 'Syncing...' : 'Sync Now'}
            </button>
          </div>
          {syncRunMsg && (
            <p className={`text-sm ${syncRunMsg.includes('failed') ? 'text-red-400' : 'text-emerald-400'}`}>
              {syncRunMsg}
            </p>
          )}
        </form>
      </div>

      {/* Monitoring */}
      <div className="card mb-6 flex items-start gap-4">
        <div className="p-3 rounded-lg bg-accent/15 text-accent">
          <LineChart size={22} />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-white text-lg">Monitoring</h3>
          <p className="text-sm text-gray-400 mt-1">
            Prometheus metrics, Grafana dashboards, and scrape targets live on the Monitoring page.
          </p>
          <Link to="/monitoring" className="btn-primary inline-flex items-center gap-2 mt-4">
            <LineChart size={14} /> Open Monitoring
          </Link>
        </div>
      </div>

      {/* Coming soon integrations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {comingSoon.map(({ icon: Icon, title, description }) => (
          <div key={title} className="card opacity-75">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-lg bg-surface-overlay text-gray-500">
                <Icon size={22} />
              </div>
              <div>
                <h3 className="font-semibold text-white">{title}</h3>
                <p className="text-sm text-gray-400 mt-1">{description}</p>
                <span className="inline-block mt-3 text-xs px-2 py-1 rounded bg-surface-overlay text-gray-500 border border-border">
                  Coming Soon
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card mt-6">
        <h3 className="font-semibold text-white mb-2">About OpsDeck</h3>
        <p className="text-sm text-gray-400">
          OpsDeck v0.1.0 — Configure SSH credentials above to enable real health checks,
          metrics collection, and automation jobs on your Linux nodes.
        </p>
      </div>
    </div>
  )
}
