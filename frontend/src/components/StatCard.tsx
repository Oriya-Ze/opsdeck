import type { LucideIcon } from 'lucide-react'

interface Props {
  title: string
  value: string | number
  icon: LucideIcon
  color?: string
  subtitle?: string
}

export function StatCard({ title, value, icon: Icon, color = 'text-accent', subtitle }: Props) {
  return (
    <div className="card flex items-start justify-between">
      <div>
        <p className="text-sm text-gray-400">{title}</p>
        <p className="text-3xl font-bold mt-1 text-white">{value}</p>
        {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
      </div>
      <div className={`p-3 rounded-lg bg-surface-overlay ${color}`}>
        <Icon size={22} />
      </div>
    </div>
  )
}
