import { useUI } from '@/contexts/UIContext'
import { useAuth } from '@/contexts/AuthContext'
import { Menu, Bell, Search } from 'lucide-react'

interface HeaderProps {
  onMenuToggle: () => void
}

export function Header({ onMenuToggle }: HeaderProps) {
  const { tableDensity, setTableDensity } = useUI()
  const { role } = useAuth()

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-neutral-200 bg-neutral-50 px-4 lg:px-8">
      {/* Mobile Hamburger menu */}
      <button
        onClick={onMenuToggle}
        className="min-h-11 min-w-11 rounded-radius-sm p-2 text-neutral-600 hover:bg-neutral-100 lg:hidden"
        aria-label="Toggle Navigation Menu"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Global Search */}
      <div className="relative w-64 max-w-xs lg:w-96">
        <label htmlFor="global-search" className="sr-only">Search cases</label>
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <Search className="h-4 w-4 text-neutral-400" aria-hidden="true" />
        </div>
        <input
          id="global-search"
          type="search"
          placeholder="Search cases, FIRs, suspects..."
          className="w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 py-1.5 pl-10 pr-3 text-body text-neutral-900 placeholder-neutral-400 focus:border-status-info focus:ring-1 focus:ring-status-info transition-colors duration-fast"
        />
      </div>

      {/* Utility Actions */}
      <div className="flex items-center space-x-4">
        {/* Table Density Selector */}
        <div className="flex items-center space-x-2 rounded-radius-md bg-neutral-100 p-1 text-caption font-semibold">
          <button
            onClick={() => setTableDensity('dense')}
            className={`min-h-11 rounded-radius-sm px-2 py-1 transition-all duration-fast ${
              tableDensity === 'dense'
                ? 'bg-neutral-50 shadow-sm text-neutral-900'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            Dense
          </button>
          <button
            onClick={() => setTableDensity('comfortable')}
            className={`min-h-11 rounded-radius-sm px-2 py-1 transition-all duration-fast ${
              tableDensity === 'comfortable'
                ? 'bg-neutral-50 shadow-sm text-neutral-900'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            Comfortable
          </button>
        </div>

        {/* Notifications */}
        <button
          className="relative min-h-11 min-w-11 rounded-radius-full p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-status-info"
          aria-label="View notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-radius-full bg-status-danger" />
        </button>

        {/* Active Role Indicator */}
        <div className="hidden items-center space-x-2 text-small text-neutral-500 lg:flex">
          <span>Active Role:</span>
          <span className="rounded-radius-sm bg-neutral-200 px-2 py-0.5 font-bold text-neutral-800">
            {role || 'None'}
          </span>
        </div>
      </div>
    </header>
  )
}
