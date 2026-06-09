import { getStatusColor } from '../utils/status'

interface Props {
  status: string
  className?: string
}

export function StatusBadge({ status, className = '' }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize ${getStatusColor(status)} ${className}`}
    >
      {status}
    </span>
  )
}
