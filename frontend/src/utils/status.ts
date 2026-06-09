export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    healthy: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    up: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    degraded: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    pending: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    unknown: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    offline: 'bg-red-500/20 text-red-400 border-red-500/30',
    down: 'bg-red-500/20 text-red-400 border-red-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    stopped: 'bg-red-500/20 text-red-400 border-red-500/30',
    restarting: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
  }
  return map[status.toLowerCase()] || map.unknown
}

export function getUsageColor(value: number): string {
  if (value >= 80) return 'bg-red-500'
  if (value >= 60) return 'bg-amber-500'
  return 'bg-emerald-500'
}
