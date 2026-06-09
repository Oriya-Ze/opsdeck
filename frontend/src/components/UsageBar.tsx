import { getUsageColor } from '../utils/status'
import { formatPercent } from '../utils/format'

interface Props {
  label: string
  value: number
}

export function UsageBar({ label, value }: Props) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-300 font-mono">{formatPercent(value)}</span>
      </div>
      <div className="h-2 bg-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getUsageColor(value)}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  )
}
