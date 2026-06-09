import { useMemo, useState } from 'react'
import { RefreshCw, Workflow } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import type { Job } from '../types'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { SearchInput } from '../components/SearchInput'
import { Modal } from '../components/Modal'
import { EmptyState } from '../components/EmptyState'
import { formatDate } from '../utils/format'

export function JobsPage() {
  const { data: jobs, loading, error, refetch } = useFetch(() => api.getJobs())
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [rerunning, setRerunning] = useState<string | null>(null)

  const filtered = useMemo(() => {
    if (!jobs) return []
    return jobs.filter((j) => {
      const matchSearch =
        j.job_id.toLowerCase().includes(search.toLowerCase()) ||
        j.action_name.toLowerCase().includes(search.toLowerCase())
      const matchStatus = statusFilter === 'all' || j.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [jobs, search, statusFilter])

  const handleRerun = async (job: Job) => {
    setRerunning(job.id)
    try {
      await api.rerunJob(job.id)
      refetch()
    } finally {
      setRerunning(null)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Automation Jobs"
        description="Track automation tasks across your infrastructure"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search jobs..." />
        <select className="select sm:w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {error && <div className="card text-red-400 mb-4">{error}</div>}

      {filtered.length === 0 ? (
        <EmptyState
          icon={Workflow}
          title="No jobs found"
          description="Run actions from node detail pages to create automation jobs."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="table-header">Job ID</th>
                <th className="table-header">Action</th>
                <th className="table-header">Target</th>
                <th className="table-header">Status</th>
                <th className="table-header">Started</th>
                <th className="table-header">Finished</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => (
                <tr key={job.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                  <td className="table-cell">
                    <button
                      className="font-mono text-accent hover:underline"
                      onClick={() => setSelectedJob(job)}
                    >
                      {job.job_id}
                    </button>
                  </td>
                  <td className="table-cell capitalize">{job.action_name.replace(/-/g, ' ')}</td>
                  <td className="table-cell capitalize">{job.target_type}</td>
                  <td className="table-cell"><StatusBadge status={job.status} /></td>
                  <td className="table-cell text-gray-500 text-sm">{formatDate(job.started_at)}</td>
                  <td className="table-cell text-gray-500 text-sm">{formatDate(job.finished_at)}</td>
                  <td className="table-cell">
                    <div className="flex gap-2">
                      <button className="btn-secondary text-xs py-1 px-2" onClick={() => setSelectedJob(job)}>Logs</button>
                      <button
                        className="btn-secondary text-xs py-1 px-2 flex items-center gap-1"
                        onClick={() => handleRerun(job)}
                        disabled={rerunning === job.id}
                      >
                        <RefreshCw size={12} />
                        {rerunning === job.id ? '...' : 'Rerun'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal title={`Job ${selectedJob?.job_id || ''}`} open={!!selectedJob} onClose={() => setSelectedJob(null)} wide>
        {selectedJob && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-gray-400">Action:</span> <span className="capitalize">{selectedJob.action_name.replace(/-/g, ' ')}</span></div>
              <div><span className="text-gray-400">Status:</span> <StatusBadge status={selectedJob.status} /></div>
              <div><span className="text-gray-400">Target:</span> <span className="capitalize">{selectedJob.target_type}</span></div>
              <div><span className="text-gray-400">Created by:</span> {selectedJob.created_by}</div>
            </div>
            {selectedJob.output_log && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-2">Output Log</h3>
                <pre className="bg-surface border border-border rounded-lg p-4 text-xs font-mono text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                  {selectedJob.output_log}
                </pre>
              </div>
            )}
            {selectedJob.error_log && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-2">Error Log</h3>
                <pre className="bg-surface border border-red-500/30 rounded-lg p-4 text-xs font-mono text-red-400 overflow-x-auto whitespace-pre-wrap">
                  {selectedJob.error_log}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
