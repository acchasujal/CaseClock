import React, { useRef, useState } from 'react'
import { useUI } from '@/contexts/UIContext'
import { LoadingSkeleton } from './LoadingSkeleton'
import { EmptyState } from './EmptyState'

export interface ColumnDef<T> {
  header: string
  accessorKey: string
  cell?: (row: T) => React.ReactNode
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  isLoading: boolean
  onRowClick?: (row: T) => void
  emptyMessage?: string
}

export function DataTable<T extends { id: string }>({
  columns,
  data,
  isLoading,
  onRowClick,
  emptyMessage = "No records found.",
}: DataTableProps<T>) {
  const { tableDensity } = useUI()
  const rowRefs = useRef<Array<HTMLTableRowElement | null>>([])
  const [selectedRowId, setSelectedRowId] = useState<string | null>(null)

  if (isLoading) {
    return <LoadingSkeleton layout="table" />
  }

  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />
  }

  const rowHeightClass = tableDensity === 'dense' ? 'h-10 py-1' : 'h-14 py-3'

  // Resolve object paths (e.g. 'clock.days_remaining')
  const getCellValue = (item: T, path: string) => {
    return path.split('.').reduce((acc: unknown, part) => {
      if (acc === null || acc === undefined) return undefined
      return (acc as Record<string, unknown>)[part]
    }, item as unknown)
  }

  return (
    <div className="w-full overflow-x-auto rounded-radius-md border border-neutral-200 bg-neutral-50">
      <table className="w-full border-collapse text-left text-body text-neutral-800" aria-label="Case records">
        <thead className="border-b border-neutral-200 bg-neutral-100 text-small font-semibold text-neutral-600">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                scope="col"
                className="px-4 py-3 font-semibold uppercase tracking-wider"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {data.map((row, rowIndex) => (
            <tr
              key={row.id}
              ref={(element) => { rowRefs.current[rowIndex] = element }}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              aria-current={onRowClick && selectedRowId === row.id ? 'true' : undefined}
              onFocus={() => setSelectedRowId(row.id)}
              onKeyDown={(event) => {
                if (!onRowClick || event.target !== event.currentTarget) return
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onRowClick(row)
                } else if (event.key === 'ArrowDown' && rowIndex < data.length - 1) {
                  event.preventDefault()
                  rowRefs.current[rowIndex + 1]?.focus()
                } else if (event.key === 'ArrowUp' && rowIndex > 0) {
                  event.preventDefault()
                  rowRefs.current[rowIndex - 1]?.focus()
                }
              }}
              className={`transition-colors duration-fast hover:bg-neutral-100/50 focus-visible:bg-neutral-100 focus-visible:outline-none ${
                onRowClick ? 'cursor-pointer' : ''
              }`}
            >
              {columns.map((column, colIdx) => {
                const cellContent = column.cell
                  ? column.cell(row)
                  : String(getCellValue(row, column.accessorKey) ?? '')

                return (
                  <td
                    key={colIdx}
                    className={`px-4 text-small align-middle transition-all duration-fast ${rowHeightClass}`}
                  >
                    {cellContent}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
