import { useState } from 'react'
import { useRollup, type StationRanking } from '@/hooks/useRollup'
import { DataTable, type ColumnDef } from '@/components/DataTable'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { Building2, AlertTriangle, Clock, ShieldAlert, TrendingUp } from 'lucide-react'

const DISTRICTS = [
  'Bengaluru City',
  'Mysuru',
  'Mangaluru',
  'Belagavi',
  'Hubballi-Dharwad',
  'Kalaburagi',
]

export default function Rollup() {
  const [selectedDistrict, setSelectedDistrict] = useState('Bengaluru City')
  const { data, isLoading, error, refetch } = useRollup(selectedDistrict)

  const columns: ColumnDef<StationRanking>[] = [
    {
      header: 'Rank',
      accessorKey: 'rank',
      cell: (_, index) => <span className="font-bold text-neutral-600 font-mono">#{index + 1}</span>,
    },
    {
      header: 'Police Station',
      accessorKey: 'station_name',
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-neutral-400" />
          <span className="font-semibold text-neutral-800">{row.station_name}</span>
        </div>
      ),
    },
    {
      header: 'Total Cases',
      accessorKey: 'total',
      cell: (row) => <span className="font-mono">{row.total}</span>,
    },
    {
      header: 'Critical Clocks',
      accessorKey: 'critical',
      cell: (row) => (
        <span
          className={`font-semibold font-mono ${
            row.critical > 0 ? 'text-status-danger' : 'text-status-success'
          }`}
        >
          {row.critical}
        </span>
      ),
    },
    {
      header: 'Operational Status',
      accessorKey: 'status',
      cell: (row) => {
        const ratio = row.critical / (row.total || 1)
        let statusText = 'Optimal'
        let colorClass = 'text-status-success bg-status-success/10'

        if (ratio > 0.15) {
          statusText = 'Critical Action Required'
          colorClass = 'text-status-danger bg-status-danger/10'
        } else if (ratio > 0.05) {
          statusText = 'Under Review'
          colorClass = 'text-status-warning bg-status-warning/10'
        }

        return (
          <span className={`inline-flex px-2 py-0.5 text-caption font-semibold rounded-radius-sm ${colorClass}`}>
            {statusText}
          </span>
        )
      },
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900">District Rollup</h1>
          <p className="text-body text-neutral-500">
            Exception-only operational overview of police stations in the district
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="district-select" className="text-small font-semibold text-neutral-700">
            District:
          </label>
          <select
            id="district-select"
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="rounded-radius-md border border-neutral-300 bg-white px-3 py-1.5 text-small font-medium text-neutral-800 shadow-sm focus:border-status-info focus:outline-none focus:ring-1 focus:ring-status-info"
          >
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <LoadingSkeleton layout="card" />
          <LoadingSkeleton layout="table" />
        </div>
      ) : error ? (
        <ErrorState
          message={`Failed to fetch rollup details for ${selectedDistrict}. Please check server connection.`}
          onRetry={() => void refetch()}
        />
      ) : data ? (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-caption font-semibold text-neutral-500 uppercase">Active Cases</span>
                <Building2 className="h-5 w-5 text-neutral-400" />
              </div>
              <div className="text-h1 font-bold text-neutral-800 mt-2 font-mono">{data.total_cases}</div>
            </div>
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-caption font-semibold text-status-danger uppercase font-bold">Red Clocks</span>
                <Clock className="h-5 w-5 text-status-danger" />
              </div>
              <div className="text-h1 font-bold text-status-danger mt-2 font-mono">{data.red_clocks}</div>
            </div>
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-caption font-semibold text-status-warning uppercase">Amber Clocks</span>
                <Clock className="h-5 w-5 text-status-warning" />
              </div>
              <div className="text-h1 font-bold text-status-warning mt-2 font-mono">{data.amber_clocks}</div>
            </div>
            <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-caption font-semibold text-status-info uppercase">Stale Blockers</span>
                <ShieldAlert className="h-5 w-5 text-status-info" />
              </div>
              <div className="text-h1 font-bold text-status-info mt-2 font-mono">{data.stale_dependencies}</div>
            </div>
          </div>

          {/* Station Rankings Performance Table */}
          <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-neutral-500" />
              <h2 className="text-h2 font-semibold text-neutral-800">Station Performance Rankings</h2>
            </div>
            {data.station_rankings.length === 0 ? (
              <div className="py-12 text-center text-neutral-500 border border-dashed border-neutral-300 rounded-radius-md">
                <AlertTriangle className="mx-auto h-12 w-12 text-neutral-300 mb-4" />
                <p className="font-semibold text-neutral-700">No Station Records Found</p>
                <p className="text-caption text-neutral-400 mt-1">No police stations have active cases in this district.</p>
              </div>
            ) : (
              <DataTable columns={columns} data={data.station_rankings} isLoading={false} />
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}
