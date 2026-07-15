import { useState, useMemo, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorklist } from '@/hooks/useWorklist'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { ClockBadge } from '@/components/ClockBadge'
import { RiskBadge } from '@/components/RiskBadge'
import { StatusChip } from '@/components/StatusChip'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type { CaseSummaryResponse } from '@shared/contracts/api'
import { ShieldAlert } from 'lucide-react'

const PAGE_SIZE = 15

export default function Worklist() {
  const navigate = useNavigate()
  const { data: cases, isLoading, error, refetch } = useWorklist()

  // Search and Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [stationFilter, setStationFilter] = useState('all')
  const [clockStatusFilter, setClockStatusFilter] = useState('all')
  const [riskFilter, setRiskFilter] = useState('all')
  const [sortBy, setSortBy] = useState('risk_rank')
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1)
  
  // Keyboard Navigation State
  const [selectedRowIndex, setSelectedRowIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)



  // Extract unique stations dynamically for filter dropdown
  const uniqueStations = useMemo(() => {
    if (!cases) return []
    return Array.from(new Set(cases.map((c) => c.station_name))).sort()
  }, [cases])

  // Filter & Search Logic
  const filteredCases = useMemo(() => {
    if (!cases) return []

    return cases.filter((c) => {
      // 1. Search Query (FIR Number or Offence Category)
      const matchesSearch = 
        c.fir_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.offence_category.toLowerCase().includes(searchQuery.toLowerCase())

      // 2. Station Name Filter
      const matchesStation = stationFilter === 'all' || c.station_name === stationFilter

      // 3. Clock Status Filter
      const matchesClock = clockStatusFilter === 'all' || c.clock.status === clockStatusFilter

      // 4. Risk Level Filter (Mapped from clock status to avoid frontend risk calculation logic)
      let riskLevel = 'LOW'
      if (c.clock.status === 'red' || c.clock.status === 'overdue') {
        riskLevel = 'HIGH'
      } else if (c.clock.status === 'amber') {
        riskLevel = 'MEDIUM'
      }
      const matchesRisk = riskFilter === 'all' || riskLevel === riskFilter

      return matchesSearch && matchesStation && matchesClock && matchesRisk
    })
  }, [cases, searchQuery, stationFilter, clockStatusFilter, riskFilter])

  // Sorting Logic
  const sortedCases = useMemo(() => {
    const list = [...filteredCases]
    
    list.sort((a, b) => {
      if (sortBy === 'risk_rank') {
        return a.risk_rank - b.risk_rank
      }
      if (sortBy === 'days_remaining') {
        // Sort breached / overdue first, then lowest days left
        if (a.clock.status === 'overdue' && b.clock.status !== 'overdue') return -1
        if (b.clock.status === 'overdue' && a.clock.status !== 'overdue') return 1
        return a.clock.days_remaining - b.clock.days_remaining
      }
      if (sortBy === 'unresolved_dependencies') {
        return b.unresolved_dependency_count - a.unresolved_dependency_count
      }
      return 0
    })

    return list
  }, [filteredCases, sortBy])

  // Pagination Logic
  const totalPages = Math.ceil(sortedCases.length / PAGE_SIZE)
  const paginatedCases = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return sortedCases.slice(start, start + PAGE_SIZE)
  }, [sortedCases, currentPage])

  // Keyboard Event Handlers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only navigate if table is populated and not currently typing in search input
      if (paginatedCases.length === 0 || document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TR') {
        return
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedRowIndex((prev) => 
          prev === -1 ? 0 : Math.min(prev + 1, paginatedCases.length - 1)
        )
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedRowIndex((prev) => 
          prev === -1 ? 0 : Math.max(prev - 1, 0)
        )
      } else if (e.key === 'Enter') {
        if (selectedRowIndex >= 0 && selectedRowIndex < paginatedCases.length) {
          e.preventDefault()
          const targetCase = paginatedCases[selectedRowIndex]
          navigate(`/case/${targetCase.id}`)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [paginatedCases, selectedRowIndex, navigate])

  // Reset focus inside container on row selection
  useEffect(() => {
    if (selectedRowIndex !== -1 && containerRef.current) {
      containerRef.current.focus()
    }
  }, [selectedRowIndex])

  // Handle Loading State
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900">Risk-Ranked Worklist</h1>
          <p className="text-body text-neutral-500">Loading active cases...</p>
        </div>
        <LoadingSkeleton layout="table" rows={PAGE_SIZE} />
      </div>
    )
  }

  // Handle Error State
  if (error) {
    return (
      <div className="py-12">
        <ErrorState 
          message={error instanceof Error ? error.message : "Failed to load the active case worklist. Please verify server connectivity."}
          onRetry={refetch}
        />
      </div>
    )
  }

  // Define table columns matching Design Spec and using semantic wrappers
  const columns: ColumnDef<CaseSummaryResponse>[] = [
    {
      header: 'Priority',
      accessorKey: 'risk_rank',
      cell: (row) => (
        <span className="font-bold text-neutral-600 font-mono">
          #{row.risk_rank}
        </span>
      )
    },
    {
      header: 'Risk Level',
      accessorKey: 'clock.status',
      cell: (row) => {
        let riskLevel: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW'
        if (row.clock.status === 'red' || row.clock.status === 'overdue') {
          riskLevel = 'HIGH'
        } else if (row.clock.status === 'amber') {
          riskLevel = 'MEDIUM'
        }
        return <RiskBadge level={riskLevel} />
      }
    },
    {
      header: 'Statutory Clock',
      accessorKey: 'clock.days_remaining',
      cell: (row) => (
        <ClockBadge daysRemaining={row.clock.days_remaining} status={row.clock.status} variant="compact" />
      )
    },
    {
      header: 'FIR Number',
      accessorKey: 'fir_number',
      cell: (row) => (
        <span className="font-semibold text-neutral-900 font-mono hover:text-status-info transition-colors duration-fast">
          {row.fir_number}
        </span>
      )
    },
    {
      header: 'Station',
      accessorKey: 'station_name'
    },
    {
      header: 'Offence Category',
      accessorKey: 'offence_category'
    },
    {
      header: 'Blockers',
      accessorKey: 'unresolved_dependency_count',
      cell: (row) => (
        <StatusChip 
          status={row.unresolved_dependency_count > 0 ? 'stale' : 'healthy'}
          label={row.unresolved_dependency_count > 0 ? `${row.unresolved_dependency_count} Pending` : 'Clear'}
        />
      )
    },
    {
      header: 'Assigned Officer',
      accessorKey: 'id',
      cell: () => (
        <span className="text-caption text-neutral-400 italic">
          N/A [Schema Gap]
        </span>
      )
    },
    {
      header: 'Case Status',
      accessorKey: 'unresolved_dependency_count',
      cell: (row) => (
        <StatusChip 
          status={row.unresolved_dependency_count > 0 ? 'pending' : 'resolved'}
          label={row.unresolved_dependency_count > 0 ? 'Under Investigation' : 'Ready to File'}
        />
      )
    },
    {
      header: 'Last Updated',
      accessorKey: 'id',
      cell: () => (
        <span className="text-caption text-neutral-400 font-mono">
          N/A [Schema Gap]
        </span>
      )
    },
    {
      header: 'Actions',
      accessorKey: 'id',
      cell: (row) => (
        <Button 
          variant="ghost" 
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/case/${row.id}`)
          }}
        >
          View Details
        </Button>
      )
    }
  ]

  // Custom cell renderer override that adds keyboard-focus highlighting
  const customColumns = columns.map((col) => ({
    ...col,
    cell: (row: CaseSummaryResponse) => {
      const isSelected = paginatedCases[selectedRowIndex]?.id === row.id
      return (
        <div className={`transition-all duration-fast ${isSelected ? 'font-medium text-status-info' : ''}`}>
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
      aria-label="Investigation Worklist Command Center"
    >
      {/* Page Title Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2"><h1 className="text-h1 font-bold text-neutral-900">Risk-Ranked Worklist</h1><span className="rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-1 text-caption font-semibold text-neutral-700">Synthetic Data</span></div>
        <p className="text-body text-neutral-500">
          Statutory-deadline investigation command center for Mysuru District
        </p>
      </div>

      {/* Filter and Search Action Bar */}
      <div className="flex flex-col gap-4 rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 lg:flex-row lg:items-end">
        {/* Search Input */}
        <div className="flex-1">
          <Input
            label="Search cases"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setCurrentPage(1)
              setSelectedRowIndex(-1)
            }}
            placeholder="Search by FIR or category..."
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
              setCurrentPage(1)
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

        {/* Clock Status Filter */}
        <div className="w-full lg:w-48">
          <label htmlFor="clock-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Clock Status
          </label>
          <select
            id="clock-filter"
            value={clockStatusFilter}
            onChange={(e) => {
              setClockStatusFilter(e.target.value)
              setCurrentPage(1)
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

        {/* Risk Level Filter */}
        <div className="w-full lg:w-48">
          <label htmlFor="risk-filter" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Risk Rank
          </label>
          <select
            id="risk-filter"
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value)
              setCurrentPage(1)
              setSelectedRowIndex(-1)
            }}
            className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
          >
            <option value="all">All Risks</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>
        </div>

        {/* Sort Trigger */}
        <div className="w-full lg:w-48">
          <label htmlFor="sort-by" className="block text-small font-semibold text-neutral-700 mb-1.5">
            Sort Priority
          </label>
          <select
            id="sort-by"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value)
              setCurrentPage(1)
              setSelectedRowIndex(-1)
            }}
            className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
          >
            <option value="risk_rank">Risk Rank (Urgent First)</option>
            <option value="days_remaining">Days Left (Fewest First)</option>
            <option value="unresolved_dependencies">Blockers Count (Most First)</option>
          </select>
        </div>
      </div>

      {/* Main Table Area */}
      <div className="space-y-4">
        {paginatedCases.length === 0 ? (
          <div className="py-12 border border-dashed border-neutral-300 rounded-radius-md bg-neutral-50 text-center">
            <ShieldAlert className="mx-auto h-12 w-12 text-neutral-400 mb-4" />
            <h3 className="text-h2 font-semibold text-neutral-700">No cases match filters</h3>
            <p className="text-body text-neutral-500 mt-1 mb-6">
              Adjust search query or filter parameters to locate the active case files.
            </p>
            <Button variant="secondary" onClick={() => {
              setSearchQuery('')
              setStationFilter('all')
              setClockStatusFilter('all')
              setRiskFilter('all')
              setSortBy('risk_rank')
            }}>
              Clear Filters
            </Button>
          </div>
        ) : (
          <div className="relative">
            <DataTable
              columns={customColumns}
              data={paginatedCases}
              isLoading={false}
              onRowClick={(row) => navigate(`/case/${row.id}`)}
            />
            {/* Keyboard shortcut hint */}
            <div className="hidden lg:block text-caption text-neutral-400 mt-2 italic text-right">
              Use <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↑</kbd> <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">↓</kbd> keys to navigate, <kbd className="bg-neutral-200 px-1 rounded-radius-sm text-neutral-600 font-mono">Enter</kbd> to open.
            </div>
          </div>
        )}
      </div>

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-neutral-200 pt-4">
          <div className="text-small text-neutral-500">
            Showing page <span className="font-bold text-neutral-800">{currentPage}</span> of{' '}
            <span className="font-bold text-neutral-800">{totalPages}</span> ({sortedCases.length} total cases)
          </div>
          <div className="flex space-x-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
