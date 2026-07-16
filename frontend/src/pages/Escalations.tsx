import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEscalations } from '@/hooks/useEscalations'
import { useWorklist } from '@/hooks/useWorklist'
import { useUpdateDependency } from '@/hooks/useUpdateDependency'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { ClockBadge } from '@/components/ClockBadge'
import { RiskBadge } from '@/components/RiskBadge'
import { StatusChip } from '@/components/StatusChip'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { clockStatusToRisk } from '@/lib/utils'
import { toast } from 'sonner'
import { CheckCircle } from 'lucide-react'

// Define the joined type for type-safe rendering
interface JoinedEscalation {
  id: string
  case_id: string
  triggered_at: string
  reason: string
  routed_to_rank: string
  routed_to_officer_id: string
  resolved: boolean

  // Joined Case Fields
  fir_number: string
  station_name: string
  clock_status: 'green' | 'amber' | 'red' | 'overdue'
  days_remaining: number
  unresolved_dependency_count: number
  risk_rank: number
}

// Shared select class
const SELECT_CLASS =
  'block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info'

export default function Escalations() {
  const navigate = useNavigate()
  const {
    data: escalations,
    isLoading: isEscalationsLoading,
    error: escalationsError,
    refetch: refetchEscalations,
  } = useEscalations()
  const {
    data: cases,
    isLoading: isCasesLoading,
    error: casesError,
    refetch: refetchCases,
  } = useWorklist()
  const updateDependency = useUpdateDependency()

  // Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [stationFilter, setStationFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [clockFilter, setClockFilter] = useState('all')

  // Join Escalation data with Case data on client-side
  const joinedData = useMemo(() => {
    if (!escalations || !cases) return []

    return escalations
      .map((esc) => {
        const matchedCase = cases.find((c) => c.id === esc.case_id)
        if (!matchedCase) return null

        return {
          ...esc,
          fir_number: matchedCase.fir_number,
          station_name: matchedCase.station_name,
          clock_status: matchedCase.clock.status,
          days_remaining: matchedCase.clock.days_remaining,
          unresolved_dependency_count: matchedCase.unresolved_dependency_count,
          risk_rank: matchedCase.risk_rank,
        } as JoinedEscalation
      })
      .filter((esc): esc is JoinedEscalation => esc !== null)
  }, [escalations, cases])

  // Extract unique stations dynamically for filter dropdown
  const uniqueStations = useMemo(() => {
    return Array.from(new Set(joinedData.map((esc) => esc.station_name))).sort()
  }, [joinedData])

  // Filtered Escalations
  const filteredData = useMemo(() => {
    return joinedData.filter((esc) => {
      const matchesSearch =
        esc.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
        esc.fir_number.toLowerCase().includes(searchQuery.toLowerCase())

      const matchesStation = stationFilter === 'all' || esc.station_name === stationFilter

      const priority = clockStatusToRisk(esc.clock_status)
      const matchesPriority = priorityFilter === 'all' || priority === priorityFilter

      const matchesClock = clockFilter === 'all' || esc.clock_status === clockFilter

      return matchesSearch && matchesStation && matchesPriority && matchesClock
    })
  }, [joinedData, searchQuery, stationFilter, priorityFilter, clockFilter])

  // Stats Card Calculations
  const stats = useMemo(() => {
    const total = filteredData.length
    const critical = filteredData.filter((esc) => esc.clock_status === 'red').length
    const overdue = filteredData.filter((esc) => esc.clock_status === 'overdue').length
    const awaitingAction = filteredData.filter((esc) => !esc.resolved).length

    return { total, critical, overdue, awaitingAction }
  }, [filteredData])

  // Handle Loading States
  if (isEscalationsLoading || isCasesLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900">Escalation Queue</h1>
          <p className="text-body text-neutral-500">Loading live supervisor queue...</p>
        </div>
        <LoadingSkeleton layout="card" />
        <LoadingSkeleton layout="table" />
      </div>
    )
  }

  // Handle Error States
  if (escalationsError || casesError) {
    return (
      <div className="py-12">
        <ErrorState
          message="Failed to synchronize with the escalation queue. Please ensure backend services are reachable."
          onRetry={() => {
            void refetchEscalations()
            void refetchCases()
          }}
        />
      </div>
    )
  }

  // Quick Action: Resolve Outstanding Dependency
  const handleResolveDependency = (esc: JoinedEscalation) => {
    // Generate mock dependency ID corresponding to case
    const mockDependencyId = esc.case_id === '847' ? 'dep_847_1' : `dep_${esc.case_id}_1`

    toast.promise(
      updateDependency.mutateAsync({
        id: mockDependencyId,
        status: 'resolved',
        caseId: esc.case_id,
      }),
      {
        loading: 'Resolving dependency blocker...',
        success: `Evidentiary blocker resolved for case ${esc.fir_number}. Escalation cleared.`,
        error: 'Failed to resolve blocker. Please retry.',
      },
    )
  }

  // Columns for the table
  const columns: ColumnDef<JoinedEscalation>[] = [
    {
      header: 'FIR',
      accessorKey: 'fir_number',
      cell: (row) => (
        <span className="font-bold text-neutral-900 font-mono">{row.fir_number}</span>
      ),
    },
    {
      header: 'Police Station',
      accessorKey: 'station_name',
    },
    {
      header: 'Officer',
      accessorKey: 'id',
      cell: () => (
        <span className="text-caption text-neutral-400 italic">N/A [Schema Gap]</span>
      ),
    },
    {
      header: 'Escalation Reason',
      accessorKey: 'reason',
      cell: (row) => (
        <span className="text-small text-neutral-700 max-w-xs block truncate" title={row.reason}>
          {row.reason}
        </span>
      ),
    },
    {
      header: 'Clock Status',
      accessorKey: 'clock_status',
      cell: (row) => (
        <ClockBadge daysRemaining={row.days_remaining} status={row.clock_status} variant="compact" />
      ),
    },
    {
      header: 'Days Remaining',
      accessorKey: 'days_remaining',
      cell: (row) => (
        <span className="font-mono tabular-nums font-semibold">{row.days_remaining}d</span>
      ),
    },
    {
      header: 'Dependency Blocking',
      accessorKey: 'unresolved_dependency_count',
      cell: (row) => (
        <StatusChip
          status={row.unresolved_dependency_count > 0 ? 'stale' : 'healthy'}
          label={row.unresolved_dependency_count > 0 ? 'Blocker Outstanding' : 'Resolved'}
        />
      ),
    },
    {
      header: 'Priority',
      accessorKey: 'clock_status',
      cell: (row) => <RiskBadge level={clockStatusToRisk(row.clock_status)} />,
    },
    {
      header: 'Escalated Since',
      accessorKey: 'triggered_at',
      cell: (row) => (
        <span className="font-mono text-caption text-neutral-500">
          {new Date(row.triggered_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    {
      header: 'Recommended Action',
      accessorKey: 'clock_status',
      cell: (row) => {
        let action = 'Review Blockers'
        if (row.clock_status === 'overdue') action = 'Immediate Filing'
        else if (row.clock_status === 'red') action = 'Resolve FSL Blocker'
        return <span className="font-semibold text-caption text-neutral-600 uppercase">{action}</span>
      },
    },
    {
      header: 'Quick Action',
      accessorKey: 'id',
      cell: (row) => (
        <div className="flex space-x-2" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/case/${row.case_id}`)}
            aria-label={`Open case ${row.fir_number}`}
          >
            Open Case
          </Button>
          {row.unresolved_dependency_count > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleResolveDependency(row)}
              aria-label={`Resolve dependency for case ${row.fir_number}`}
            >
              Resolve
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-h1 font-bold text-neutral-900">Escalation Queue</h1>
          <span className="rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-1 text-caption font-semibold text-neutral-700">
            Synthetic Data
          </span>
        </div>
        <p className="text-body text-neutral-500">
          Supervisor command dashboard prioritizing cases requiring critical intervention
        </p>
      </div>

      {/* Summary Cards */}
      <div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        role="region"
        aria-label="Escalation summary statistics"
      >
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-neutral-500 uppercase" id="stat-total">Total Escalations</div>
          <div
            className="text-display font-bold text-neutral-800 mt-1 tabular-nums"
            aria-labelledby="stat-total"
          >
            {stats.total}
          </div>
        </div>
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-warning uppercase" id="stat-critical">Critical Clocks</div>
          <div className="text-display font-bold text-status-warning mt-1 tabular-nums" aria-labelledby="stat-critical">
            {stats.critical}
          </div>
        </div>
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-danger uppercase" id="stat-overdue">Statutory Breaches</div>
          <div className="text-display font-bold text-status-danger mt-1 tabular-nums" aria-labelledby="stat-overdue">
            {stats.overdue}
          </div>
        </div>
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-info uppercase" id="stat-awaiting">Awaiting Action</div>
          <div className="text-display font-bold text-status-info mt-1 tabular-nums" aria-labelledby="stat-awaiting">
            {stats.awaitingAction}
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div
        className="flex flex-col gap-4 rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 lg:flex-row lg:items-end"
        role="search"
        aria-label="Filter escalation queue"
      >
        <div className="flex-1">
          <Input
            label="Search queue"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by FIR or reason..."
            className="w-full"
          />
        </div>

        <div className="w-full lg:w-48">
          <label htmlFor="station-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Police Station
          </label>
          <select
            id="station-filter"
            value={stationFilter}
            onChange={(e) => setStationFilter(e.target.value)}
            className={SELECT_CLASS}
          >
            <option value="all">All Stations</option>
            {uniqueStations.map((station) => (
              <option key={station} value={station}>{station}</option>
            ))}
          </select>
        </div>

        <div className="w-full lg:w-48">
          <label htmlFor="priority-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Priority Rank
          </label>
          <select
            id="priority-filter"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className={SELECT_CLASS}
          >
            <option value="all">All Priorities</option>
            <option value="HIGH">High Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="LOW">Low Priority</option>
          </select>
        </div>

        <div className="w-full lg:w-48">
          <label htmlFor="clock-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Clock Status
          </label>
          <select
            id="clock-filter"
            value={clockFilter}
            onChange={(e) => setClockFilter(e.target.value)}
            className={SELECT_CLASS}
          >
            <option value="all">All Clocks</option>
            <option value="green">Healthy (Green)</option>
            <option value="amber">Approaching (Amber)</option>
            <option value="red">Critical (Red)</option>
            <option value="overdue">Breached (Overdue)</option>
          </select>
        </div>
      </div>

      {/* Grid Table Container */}
      <div className="space-y-4">
        {filteredData.length === 0 ? (
          <div
            className="py-12 border border-dashed border-neutral-300 rounded-radius-md bg-neutral-50 text-center"
            role="status"
            aria-live="polite"
          >
            <CheckCircle className="mx-auto h-12 w-12 text-status-success mb-4" aria-hidden="true" />
            <h3 className="text-h2 font-semibold text-neutral-700">Queue is clear</h3>
            <p className="text-body text-neutral-500 mt-1">
              No active statutory clock escalations require supervisor attention.
            </p>
          </div>
        ) : (
          <div className="relative">
            <div className="hidden lg:flex justify-end mb-1">
              <p className="text-caption text-neutral-400 italic">
                Use{' '}
                <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↑</kbd>{' '}
                <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↓</kbd>{' '}
                to navigate,{' '}
                <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">Enter</kbd>{' '}
                to view case
              </p>
            </div>
            <DataTable
              columns={columns}
              data={filteredData}
              isLoading={false}
              onRowClick={(row) => navigate(`/case/${row.case_id}`)}
              ariaLabel={`Escalation queue — ${filteredData.length} active escalations`}
            />
          </div>
        )}
      </div>
    </div>
  )
}
