/** API datetimes are stored as UTC but serialized without a timezone suffix. */
export function parseApiDate(date: string): Date {
  const trimmed = date.trim()
  if (!trimmed) return new Date(NaN)
  if (trimmed.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return new Date(trimmed)
  }
  return new Date(`${trimmed}Z`)
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  return parseApiDate(date).toLocaleString()
}

export function formatRelative(date: string | null | undefined): string {
  if (!date) return 'Never'
  const diff = Date.now() - parseApiDate(date).getTime()
  if (diff < 0) return 'Just now'
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

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

export function formatEventType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
