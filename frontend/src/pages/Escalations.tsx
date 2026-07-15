import { useState, useMemo, useEffect, useRef } from 'react'
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

export default function Escalations() {
  const navigate = useNavigate()
  const { data: escalations, isLoading: isEscalationsLoading, error: escalationsError, refetch: refetchEscalations } = useEscalations()
  const { data: cases, isLoading: isCasesLoading, error: casesError, refetch: refetchCases } = useWorklist()
  const updateDependency = useUpdateDependency()

  // Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [stationFilter, setStationFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [clockFilter, setClockFilter] = useState('all')
  const [selectedRowIndex, setSelectedRowIndex] = useState(-1)
  
  const containerRef = useRef<HTMLDivElement>(null)



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
          risk_rank: matchedCase.risk_rank
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
      // 1. Search (by Reason or FIR)
      const matchesSearch =
        esc.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
        esc.fir_number.toLowerCase().includes(searchQuery.toLowerCase())

      // 2. Station Filter
      const matchesStation = stationFilter === 'all' || esc.station_name === stationFilter

      // 3. Priority Filter (HIGH maps to red/overdue clocks)
      let priority = 'LOW'
      if (esc.clock_status === 'red' || esc.clock_status === 'overdue') {
        priority = 'HIGH'
      } else if (esc.clock_status === 'amber') {
        priority = 'MEDIUM'
      }
      const matchesPriority = priorityFilter === 'all' || priority === priorityFilter

      // 4. Clock Status Filter
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

  // Keyboard navigation listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (filteredData.length === 0 || document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TR') {
        return
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedRowIndex((prev) => 
          prev === -1 ? 0 : Math.min(prev + 1, filteredData.length - 1)
        )
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedRowIndex((prev) => 
          prev === -1 ? 0 : Math.max(prev - 1, 0)
        )
      } else if (e.key === 'Enter') {
        if (selectedRowIndex >= 0 && selectedRowIndex < filteredData.length) {
          e.preventDefault()
          navigate(`/case/${filteredData[selectedRowIndex].case_id}`)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [filteredData, selectedRowIndex, navigate])

  // Focus utility
  useEffect(() => {
    if (selectedRowIndex !== -1 && containerRef.current) {
      containerRef.current.focus()
    }
  }, [selectedRowIndex])

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
            refetchEscalations()
            refetchCases()
          }}
        />
      </div>
    )
  }

  // Quick Action: Resolve Outstanding Dependency
  const handleResolveDependency = async (esc: JoinedEscalation) => {
    // Generate mock dependency ID corresponding to case
    const mockDependencyId = esc.case_id === '847' ? 'dep_847_1' : `dep_${esc.case_id}_1`
    
    toast.promise(
      updateDependency.mutateAsync({
        id: mockDependencyId,
        status: 'resolved',
        caseId: esc.case_id
      }),
      {
        loading: 'Resolving dependency blocker...',
        success: () => {
          setSelectedRowIndex(-1)
          return `Evidentiary blocker resolved for case ${esc.fir_number}. Escalation cleared.`
        },
        error: 'Failed to resolve blocker. Please retry.'
      }
    )
  }

  // Columns for the table
  const columns: ColumnDef<JoinedEscalation>[] = [
    {
      header: 'FIR',
      accessorKey: 'fir_number',
      cell: (row) => (
        <span className="font-bold text-neutral-900 font-mono">
          {row.fir_number}
        </span>
      )
    },
    {
      header: 'Police Station',
      accessorKey: 'station_name'
    },
    {
      header: 'Officer',
      accessorKey: 'id',
      cell: () => (
        <span className="text-caption text-neutral-400 italic">
          N/A [Schema Gap]
        </span>
      )
    },
    {
      header: 'Escalation Reason',
      accessorKey: 'reason',
      cell: (row) => (
        <span className="text-small text-neutral-700 max-w-xs block truncate" title={row.reason}>
          {row.reason}
        </span>
      )
    },
    {
      header: 'Clock Status',
      accessorKey: 'clock_status',
      cell: (row) => (
        <ClockBadge daysRemaining={row.days_remaining} status={row.clock_status} variant="compact" />
      )
    },
    {
      header: 'Days Remaining',
      accessorKey: 'days_remaining',
      cell: (row) => (
        <span className="font-mono tabular-nums font-semibold">
          {row.days_remaining}d
        </span>
      )
    },
    {
      header: 'Dependency Blocking',
      accessorKey: 'unresolved_dependency_count',
      cell: (row) => (
        <StatusChip
          status={row.unresolved_dependency_count > 0 ? 'stale' : 'healthy'}
          label={row.unresolved_dependency_count > 0 ? 'Blocker Outstanding' : 'Resolved'}
        />
      )
    },
    {
      header: 'Priority',
      accessorKey: 'clock_status',
      cell: (row) => {
        let priority: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW'
        if (row.clock_status === 'red' || row.clock_status === 'overdue') {
          priority = 'HIGH'
        } else if (row.clock_status === 'amber') {
          priority = 'MEDIUM'
        }
        return <RiskBadge level={priority} />
      }
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
            minute: '2-digit'
          })}
        </span>
      )
    },
    {
      header: 'Recommended Action',
      accessorKey: 'clock_status',
      cell: (row) => {
        let action = 'Review Blockers'
        if (row.clock_status === 'overdue') action = 'Immediate Filing'
        else if (row.clock_status === 'red') action = 'Resolve FSL Blocker'
        return <span className="font-semibold text-caption text-neutral-600 uppercase">{action}</span>
      }
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
          >
            Open Case
          </Button>
          {row.unresolved_dependency_count > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleResolveDependency(row)}
            >
              Resolve
            </Button>
          )}
        </div>
      )
    }
  ]

  // Columns styling mapping highlight
  const customColumns = columns.map((col) => ({
    ...col,
    cell: (row: JoinedEscalation) => {
      const isSelected = filteredData[selectedRowIndex]?.id === row.id
      return (
        <div className={isSelected ? 'font-medium text-status-info' : ''}>
          {col.cell ? col.cell(row) : String((row as unknown as Record<string, unknown>)[col.accessorKey] ?? '')}
        </div>
      )
    }
  }))

  return (
    <div 
      className="space-y-6 outline-none" 
      ref={containerRef}
      tabIndex={0}
      aria-label="Supervisor Escalation Queue Dashboard"
    >
      {/* Title Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2"><h1 className="text-h1 font-bold text-neutral-900">Escalation Queue</h1><span className="rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-1 text-caption font-semibold text-neutral-700">Synthetic Data</span></div>
        <p className="text-body text-neutral-500">
          Supervisor command dashboard prioritizing cases requiring critical intervention
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Escalations */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-neutral-500 uppercase">Total Escalations</div>
          <div className="text-display font-bold text-neutral-800 mt-1 tabular-nums">{stats.total}</div>
        </div>

        {/* Critical */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-warning uppercase">Critical Clocks</div>
          <div className="text-display font-bold text-status-warning mt-1 tabular-nums">{stats.critical}</div>
        </div>

        {/* Overdue */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-danger uppercase">Statutory Breaches</div>
          <div className="text-display font-bold text-status-danger mt-1 tabular-nums">{stats.overdue}</div>
        </div>

        {/* Awaiting Action */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
          <div className="text-caption font-semibold text-status-info uppercase">Awaiting Action</div>
          <div className="text-display font-bold text-status-info mt-1 tabular-nums">{stats.awaitingAction}</div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col gap-4 rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 lg:flex-row lg:items-end">
        {/* Search */}
        <div className="flex-1">
          <Input
            label="Search queue"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setSelectedRowIndex(-1)
            }}
            placeholder="Search by FIR or reason..."
            className="w-full"
          />
        </div>

        {/* Station Filter */}
        <div className="w-full lg:w-48">
          <label htmlFor="station-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Police Station
          </label>
          <select
            id="station-filter"
            value={stationFilter}
            onChange={(e) => {
              setStationFilter(e.target.value)
              setSelectedRowIndex(-1)
            }}
            className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
          >
            <option value="all">All Stations</option>
            {uniqueStations.map((station) => (
              <option key={station} value={station}>
                {station}
              </option>
            ))}
          </select>
        </div>

        {/* Priority Filter */}
        <div className="w-full lg:w-48">
          <label htmlFor="priority-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Priority Rank
          </label>
          <select
            id="priority-filter"
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value)
              setSelectedRowIndex(-1)
            }}
            className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
          >
            <option value="all">All Priorities</option>
            <option value="HIGH">High Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="LOW">Low Priority</option>
          </select>
        </div>

        {/* Clock Filter */}
        <div className="w-full lg:w-48">
          <label htmlFor="clock-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Clock Status
          </label>
          <select
            id="clock-filter"
            value={clockFilter}
            onChange={(e) => {
              setClockFilter(e.target.value)
              setSelectedRowIndex(-1)
            }}
            className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
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
          <div className="py-12 border border-dashed border-neutral-300 rounded-radius-md bg-neutral-50 text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-status-success mb-4" />
            <h3 className="text-h2 font-semibold text-neutral-700">Queue is clear</h3>
            <p className="text-body text-neutral-500 mt-1">
              No active statutory clock escalations require supervisor attention.
            </p>
          </div>
        ) : (
          <div className="relative">
            <DataTable
              columns={customColumns}
              data={filteredData}
              isLoading={false}
              onRowClick={(row) => navigate(`/case/${row.case_id}`)}
            />
            {/* keyboard shortcuts */}
            <div className="hidden lg:block text-caption text-neutral-400 mt-2 italic text-right">
              Use <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↑</kbd> <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↓</kbd> keys to navigate, <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">Enter</kbd> to view case.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
