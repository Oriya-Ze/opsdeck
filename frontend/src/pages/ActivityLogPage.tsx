import { useMemo, useState } from 'react'
import { Activity } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { EmptyState } from '../components/EmptyState'
import { formatDate, formatEventType } from '../utils/format'

export function ActivityLogPage() {
  const { data: logs, loading, error } = useFetch(() => api.getActivityLogs(100))
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('all')

  const filtered = useMemo(() => {
    if (!logs) return []
    return logs.filter((l) => {
      const matchSearch =
        l.message.toLowerCase().includes(search.toLowerCase()) ||
        l.event_type.toLowerCase().includes(search.toLowerCase())
      const matchSeverity = severityFilter === 'all' || l.severity === severityFilter
      return matchSearch && matchSeverity
    })
  }, [logs, search, severityFilter])

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Activity Log"
        description="Audit trail of infrastructure events"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search events..." />
        <select className="select sm:w-40" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
          <option value="all">All severities</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
      </div>

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No activity recorded"
          description="Events will appear here as you manage nodes, run jobs, and execute health checks."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Timestamp</th>
                <th className="table-header">Event</th>
                <th className="table-header">Message</th>
                <th className="table-header">Severity</th>
                <th className="table-header">Entity</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((log) => (
                <tr key={log.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell text-gray-500 text-sm whitespace-nowrap">{formatDate(log.timestamp)}</td>
                  <td className="table-cell text-sm">{formatEventType(log.event_type)}</td>
                  <td className="table-cell text-gray-300">{log.message}</td>
                  <td className="table-cell"><StatusBadge status={log.severity} /></td>
                  <td className="table-cell text-gray-500 capitalize text-sm">
                    {log.related_entity_type || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
