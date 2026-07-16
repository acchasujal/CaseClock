import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import type { DependencyResponse, DependencyStatus } from '@shared/contracts/api'

export function useUpdateDependency() {
  const queryClient = useQueryClient()

  return useMutation<DependencyResponse, Error, { id: string; status: DependencyStatus; caseId: string }>({
    mutationFn: ({ id, status }) =>
      apiFetch<DependencyResponse>(`/deps/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    onSuccess: (_, variables) => {
      // Invalidate queries as mandated by Build Guide Task 7
      queryClient.invalidateQueries({ queryKey: ['worklist'] })
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] })
      queryClient.invalidateQueries({ queryKey: ['escalations'] })
    },
  })
}
