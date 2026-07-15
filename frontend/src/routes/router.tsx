import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import Login from '@/pages/Login'
import Worklist from '@/pages/Worklist'
import Escalations from '@/pages/Escalations'
import Rollup from '@/pages/Rollup'
import Patterns from '@/pages/Patterns'
import Copilot from '@/pages/Copilot'
import CaseDetail from '@/pages/CaseDetail'
import { RoleGuard } from '@/components/RoleGuard'
import type { UserRole } from '@shared/contracts/api'

const allRoles: UserRole[] = ['IO', 'SHO', 'SP']
const worklistRoles: UserRole[] = ['IO', 'SHO']
const escalationRoles: UserRole[] = ['SHO', 'SP']

export const router = createBrowserRouter([
  // Public Route
  {
    path: '/login',
    element: <Login />,
  },
  
  // Protected Routes (Wrapped in AppShell)
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/worklist" replace />,
      },
      {
        path: 'worklist',
        element: <RoleGuard allowedRoles={worklistRoles}><Worklist /></RoleGuard>,
      },
      {
        path: 'escalations',
        element: <RoleGuard allowedRoles={escalationRoles}><Escalations /></RoleGuard>,
      },
      {
        path: 'rollup',
        element: <RoleGuard allowedRoles={['SP']}><Rollup /></RoleGuard>,
      },
      {
        path: 'patterns',
        element: <RoleGuard allowedRoles={allRoles}><Patterns /></RoleGuard>,
      },
      {
        path: 'copilot',
        element: <RoleGuard allowedRoles={allRoles}><Copilot /></RoleGuard>,
      },
      {
        path: 'case/:id',
        element: <RoleGuard allowedRoles={allRoles}><CaseDetail /></RoleGuard>,
      },
      // Settings placeholder
      {
        path: 'settings',
        element: <RoleGuard allowedRoles={allRoles}><div>
          <div className="space-y-6">
            <h1 className="text-h1 font-bold text-neutral-900">Settings</h1>
            <div className="border border-dashed border-neutral-300 rounded-radius-md p-12 text-center bg-neutral-50">
              <p className="text-body text-neutral-600">Settings page placeholder (Roadmap)</p>
            </div>
          </div>
        </div></RoleGuard>,
      },
    ],
  },
  
  // Fallback Redirect
  {
    path: '*',
    element: <Navigate to="/login" replace />,
  },
])
