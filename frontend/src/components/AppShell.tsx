import { useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppShell() {
  const { isAuthenticated } = useAuth()
  const [isSidebarOpen, setSidebarOpen] = useState(false)

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex">
      {/* Sidebar Navigation */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col lg:pl-sidebar min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} />

        {/* Dynamic Content Outlet */}
        <main className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
