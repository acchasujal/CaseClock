import { useQuery } from '@tanstack/react-query'
import type { EscalationResponse } from '@shared/contracts/api'

export function useEscalations() {
  return useQuery<EscalationResponse[]>({
    queryKey: ['escalations'],
    queryFn: async () => {
      const response = await fetch('/escalations')
      if (!response.ok) {
        throw new Error(`Failed to fetch escalations: ${response.statusText}`)
      }
      return response.json()
    },
    // The build guide mandates 3 seconds polling to simulate live updates
    refetchInterval: 3000,
    staleTime: 0,
  })
}
