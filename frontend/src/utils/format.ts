export function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  return new Date(date).toLocaleString()
}

export function formatRelative(date: string | null | undefined): string {
  if (!date) return 'Never'
  const diff = Date.now() - new Date(date).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatEventType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
