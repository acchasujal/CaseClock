import { useDeadlineMonitor } from '@/hooks/useDeadlineMonitor'
import { ShieldCheck, AlertCircle, Clock } from 'lucide-react'

function formatCompletedAt(isoStr: string | undefined): string {
  if (!isoStr) return 'Never'
  try {
    const dt = new Date(isoStr)
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' (' + dt.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')'
  } catch {
    return isoStr
  }
}

export function DeadlineMonitorBanner() {
  const { data: monitor, isLoading, isError } = useDeadlineMonitor()

  if (isLoading || isError || !monitor) {
    return null
  }

  const isCompleted = monitor.status === 'active'
  const isDelayed = monitor.status === 'delayed'
  const lastRun = monitor.last_run

  // Static semantic status dot colors (NO pulse / NO glow animations)
  const dotColorClass = isCompleted
    ? 'bg-status-success'
    : isDelayed
    ? 'bg-status-warning'
    : 'bg-neutral-400'

  const statusLabel = isCompleted
    ? 'ACTIVE'
    : isDelayed
    ? 'DELAYED'
    : 'UNAVAILABLE'

  return (
    <div
      className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 space-y-3"
      role="region"
      aria-label="Autonomous Deadline Monitor Status"
    >
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 pb-2.5">
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-1.5 rounded-radius-sm bg-neutral-100 px-2.5 py-1 border border-neutral-200">
            {/* Static semantic dot */}
            <span className={`h-2.5 w-2.5 rounded-full ${dotColorClass}`} aria-hidden="true" />
            <span className="text-caption font-bold tracking-wider text-neutral-800 uppercase">
              {statusLabel}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 text-small font-semibold text-neutral-900">
            <ShieldCheck className="h-4 w-4 text-neutral-600" aria-hidden="true" />
            <span>Autonomous Deadline Monitor</span>
          </div>

          <span className="text-caption text-neutral-400">|</span>
          <span className="text-caption text-neutral-600 font-medium">
            Zoho Catalyst Job Scheduling
          </span>
        </div>

        <div className="flex items-center space-x-1.5 text-caption text-neutral-500 font-mono">
          <Clock className="h-3.5 w-3.5 text-neutral-400" aria-hidden="true" />
          <span>Runs every 15 min</span>
        </div>
      </div>

      {/* Metrics Row */}
      {lastRun ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="rounded-radius-sm bg-neutral-100/70 p-2.5 border border-neutral-200/60">
            <div className="text-caption text-neutral-500 font-medium">Last Successful Sweep</div>
            <div className="text-small font-semibold text-neutral-900 font-mono mt-0.5">
              {formatCompletedAt(lastRun.completed_at)}
            </div>
          </div>

          <div className="rounded-radius-sm bg-neutral-100/70 p-2.5 border border-neutral-200/60">
            <div className="text-caption text-neutral-500 font-medium">Cases Scanned</div>
            <div className="text-h3 font-bold text-neutral-900 font-mono mt-0.5 tabular-nums">
              {lastRun.cases_scanned}
            </div>
          </div>

          <div className="rounded-radius-sm bg-neutral-100/70 p-2.5 border border-neutral-200/60">
            <div className="text-caption text-neutral-500 font-medium">Clocks Evaluated</div>
            <div className="text-h3 font-bold text-neutral-900 font-mono mt-0.5 tabular-nums">
              {lastRun.clocks_evaluated}
            </div>
          </div>

          <div className="rounded-radius-sm bg-neutral-100/70 p-2.5 border border-neutral-200/60">
            <div className="text-caption text-neutral-500 font-medium">New Escalations</div>
            <div className={`text-h3 font-bold font-mono mt-0.5 tabular-nums ${lastRun.escalations_created > 0 ? 'text-status-warning' : 'text-neutral-900'}`}>
              {lastRun.escalations_created}
            </div>
          </div>

          <div className="rounded-radius-sm bg-neutral-100/70 p-2.5 border border-neutral-200/60">
            <div className="text-caption text-neutral-500 font-medium">Execution Time</div>
            <div className="text-h3 font-bold text-neutral-900 font-mono mt-0.5 tabular-nums">
              {lastRun.duration_ms} <span className="text-caption font-normal">ms</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center space-x-2 text-small text-neutral-500 py-1">
          <AlertCircle className="h-4 w-4 text-neutral-400" aria-hidden="true" />
          <span>No scheduled deadline sweep record found yet. Next sweep will run automatically.</span>
        </div>
      )}

      {/* Supporting Narrative */}
      <p className="text-caption text-neutral-500 italic">
        Statutory investigation deadlines are continuously monitored even when officers are offline.
      </p>
    </div>
  )
}
