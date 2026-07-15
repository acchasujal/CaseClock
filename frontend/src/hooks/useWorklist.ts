import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import type { CaseSummaryResponse } from '@shared/contracts/api'

export function useWorklist() {
  const { role } = useAuth()

  return useQuery<CaseSummaryResponse[]>({
    queryKey: ['worklist', role],
    queryFn: async () => {
      // Pass the current user role to the endpoint
      const response = await fetch(`/worklist?role=${role || 'IO'}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch worklist: ${response.statusText}`)
      }
      return response.json()
    },
    // The build guide specifies staleTime: 0 globally in queryClient.ts, 
    // but we can explicitly reiterate it here for absolute safety.
    staleTime: 0,
  })
}
