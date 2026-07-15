import { useQuery } from '@tanstack/react-query'
import type { CaseDetailResponse } from '@shared/contracts/api'

export function useCaseDetail(caseId: string | undefined) {
  return useQuery<CaseDetailResponse>({
    queryKey: ['case', caseId],
    queryFn: async () => {
      const response = await fetch(`/cases/${caseId}`)
      if (!response.ok) {
        throw new Error(`Unable to load this case: ${response.statusText}`)
      }
      return response.json()
    },
    enabled: Boolean(caseId),
  })
}
