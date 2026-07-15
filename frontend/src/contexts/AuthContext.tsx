import React, { createContext, useContext, useState } from 'react'
import type { UserRole } from '@shared/contracts/api'

interface AuthContextType {
  role: UserRole | null
  login: (role: UserRole) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<UserRole | null>(() => {
    const saved = localStorage.getItem('caseclock_role')
    return (saved as UserRole) || null
  })

  const login = (newRole: UserRole) => {
    setRole(newRole)
    localStorage.setItem('caseclock_role', newRole)
  }

  const logout = () => {
    setRole(null)
    localStorage.removeItem('caseclock_role')
  }

  return (
    <AuthContext.Provider value={{ role, login, logout, isAuthenticated: !!role }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
