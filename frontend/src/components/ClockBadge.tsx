import type { ClockStatus } from '@shared/contracts/api'
import { Clock } from 'lucide-react'

interface ClockBadgeProps {
  daysRemaining: number
  status: ClockStatus
  variant?: 'compact' | 'detail'
}

export function ClockBadge({ daysRemaining, status, variant = 'compact' }: ClockBadgeProps) {
  // Map ClockStatus to semantic classes and label
  const statusConfig = {
    green: {
      colorClass: 'text-status-success bg-status-success/10 border-status-success/20',
      barClass: 'bg-status-success',
      label: 'Healthy'
    },
    amber: {
      colorClass: 'text-status-warning bg-status-warning/10 border-status-warning/20',
      barClass: 'bg-status-warning',
      label: 'Approaching'
    },
    red: {
      colorClass: 'text-status-danger bg-status-danger/10 border-status-danger/20',
      barClass: 'bg-status-danger',
      label: 'Critical'
    },
    overdue: {
      colorClass: 'text-neutral-50 bg-status-danger border-status-danger animate-pulse',
      barClass: 'bg-status-danger',
      label: 'Statutory Breach'
    }
  }

  const { colorClass, barClass, label } = statusConfig[status]

  if (variant === 'compact') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-radius-sm border text-caption font-semibold ${colorClass}`}
        aria-label={`${daysRemaining} days remaining, status ${label}`}
      >
        <Clock className="mr-1 h-3.5 w-3.5" />
        <span className="tabular-nums">
          {status === 'overdue' ? 'BREACHED' : `${daysRemaining}d`}
        </span>
      </span>
    )
  }

  // Detail variant: horizontal progress bar + text
  // Calculate percentage of time elapsed (assume a standard 60-day baseline for display)
  const maxDays = 60
  const progressPercent = Math.max(0, Math.min(100, (daysRemaining / maxDays) * 100))

  return (
    <div 
      className="space-y-2 rounded-radius-md border border-neutral-200 bg-neutral-50 p-4"
      role="group"
      aria-label={`Statutory Clock: ${daysRemaining} days remaining`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Clock className="h-5 w-5 text-neutral-500" />
          <span className="text-body font-medium text-neutral-700">Statutory Deadline</span>
        </div>
        <span className={`px-2.5 py-0.5 rounded-radius-sm border text-caption font-bold ${colorClass}`}>
          {status === 'overdue' ? 'BREACHED' : `${daysRemaining} Days Left`}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-full rounded-radius-full bg-neutral-200 overflow-hidden">
        <div 
          className={`h-full transition-all duration-normal ${barClass}`}
          style={{ width: `${status === 'overdue' ? 100 : progressPercent}%` }}
        />
      </div>

      <div className="flex justify-between text-caption text-neutral-400">
        <span>Start</span>
        <span>{label}</span>
        <span>Deadline</span>
      </div>
    </div>
  )
}
