import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Server,
  ServerOff,
  XCircle,
} from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import { formatDate, formatRelative } from '../utils/format'

export function DashboardPage() {
  const { data, loading, error } = useFetch(() => api.getDashboardStats())

  if (loading) return <LoadingSpinner />
  if (error || !data) {
    return (
      <div className="card text-red-400">
        Failed to load dashboard: {error}
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your HomeLab infrastructure"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Nodes" value={data.total_nodes} icon={Server} />
        <StatCard title="Healthy Nodes" value={data.healthy_nodes} icon={CheckCircle} color="text-emerald-400" />
        <StatCard title="Warning Nodes" value={data.warning_nodes} icon={AlertTriangle} color="text-amber-400" />
        <StatCard title="Offline Nodes" value={data.offline_nodes} icon={ServerOff} color="text-red-400" />
        <StatCard title="Running Services" value={data.running_services} icon={CheckCircle} color="text-emerald-400" />
        <StatCard title="Failed Services" value={data.failed_services} icon={XCircle} color="text-red-400" />
        <StatCard
          title="Last Health Check"
          value={formatRelative(data.last_health_check_at)}
          icon={Clock}
          subtitle={formatDate(data.last_health_check_at)}
        />
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Automation Jobs</h2>
          <Link to="/jobs" className="text-sm text-accent hover:text-accent-hover">
            View all →
          </Link>
        </div>

        {data.recent_jobs.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">No recent jobs</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="table-header">Job ID</th>
                  <th className="table-header">Action</th>
                  <th className="table-header">Target</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_jobs.map((job) => (
                  <tr key={job.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                    <td className="table-cell font-mono text-accent">{job.job_id}</td>
                    <td className="table-cell capitalize">{job.action_name.replace(/-/g, ' ')}</td>
                    <td className="table-cell capitalize">{job.target_type}</td>
                    <td className="table-cell"><StatusBadge status={job.status} /></td>
                    <td className="table-cell text-gray-500">{formatRelative(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
