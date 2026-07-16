import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import type { EscalationResponse } from '@shared/contracts/api'

export function useEscalations() {
  return useQuery<EscalationResponse[]>({
    queryKey: ['escalations'],
    queryFn: () => apiFetch<EscalationResponse[]>('/escalations'),
    // The build guide mandates 3 seconds polling to simulate live updates (Task 7, approved exception)
    refetchInterval: 3000,
    staleTime: 0,
  })
}
