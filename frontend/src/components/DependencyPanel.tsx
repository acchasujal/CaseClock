import { CheckCircle2, CircleAlert, UserRound, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { StatusChip } from '@/components/StatusChip'
import type { DependencyResponse } from '@shared/contracts/api'

interface DependencyPanelProps {
  dependencies: DependencyResponse[]
  isUpdating: boolean
  onResolve: (dependencyId: string) => void
  onEscalate?: (dependencyId: string) => void
}

export function DependencyPanel({ dependencies, isUpdating, onResolve, onEscalate }: DependencyPanelProps) {
  if (dependencies.length === 0) {
    return <EmptyState message="No named evidentiary dependencies are recorded for this case." />
  }

  const unresolvedCount = dependencies.filter((d) => d.status !== 'resolved').length

  return (
    <section aria-labelledby="dependencies-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50">
      <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-4">
        <div>
          <h2 id="dependencies-heading" className="text-h2 font-semibold text-neutral-900">
            Next action: resolve the blockers
          </h2>
          <p className="mt-1 text-small text-neutral-600">
            Named dependencies from the investigation record.{' '}
            {unresolvedCount > 0 ? (
              <span>
                <strong>{unresolvedCount}</strong> outstanding blocker{unresolvedCount !== 1 ? 's' : ''} remain.
              </span>
            ) : (
              'All dependencies resolved.'
            )}
          </p>
        </div>
        <CircleAlert className="h-5 w-5 shrink-0 text-status-warning" aria-hidden="true" />
      </div>
      <ul
        className="divide-y divide-neutral-200"
        aria-label={`Case dependencies — ${unresolvedCount} unresolved`}
      >
        {dependencies.map((dependency) => (
          <li key={dependency.id} className="p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-body font-semibold text-neutral-900">{dependency.name}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-small text-neutral-600">
                  <span className="inline-flex items-center gap-1">
                    <UserRound className="h-4 w-4" aria-hidden="true" />
                    {dependency.assigned_to ?? 'Owner not recorded'}
                  </span>
                  <span className="tabular-nums">
                    {dependency.days_stale > 0
                      ? `${dependency.days_stale} days waiting`
                      : 'Recently updated'}
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip status={dependency.status} />
                {dependency.status !== 'resolved' && (
                  <>
                    <Button
                      size="sm"
                      variant="primary"
                      isLoading={isUpdating}
                      onClick={() => onResolve(dependency.id)}
                      aria-label={`Mark ${dependency.name} as resolved`}
                    >
                      <CheckCircle2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Resolve
                    </Button>
                    {onEscalate && (
                      <Button
                        size="sm"
                        variant="danger"
                        isLoading={isUpdating}
                        onClick={() => onEscalate(dependency.id)}
                        aria-label={`Escalate ${dependency.name} to supervisor`}
                      >
                        <AlertTriangle className="mr-1.5 h-4 w-4" aria-hidden="true" />
                        Escalate
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
