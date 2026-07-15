import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { DependencyResponse, DependencyStatus } from '@shared/contracts/api'

export function useUpdateDependency() {
  const queryClient = useQueryClient()

  return useMutation<DependencyResponse, Error, { id: string; status: DependencyStatus; caseId: string }>({
    mutationFn: async ({ id, status }) => {
      const response = await fetch(`/deps/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      })
      if (!response.ok) {
        throw new Error(`Failed to update dependency: ${response.statusText}`)
      }
      return response.json()
    },
    onSuccess: (_, variables) => {
      // Invalidate queries as mandated by Build Guide Task 7
      queryClient.invalidateQueries({ queryKey: ['worklist'] })
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] })
      queryClient.invalidateQueries({ queryKey: ['escalations'] })
    },
  })
}
