import { useQuery } from '@tanstack/react-query'

export interface NetworkNode {
  id: string
  type: string
  data: {
    label: string
    [key: string]: unknown
  }
  position: {
    x: number
    y: number
  }
}

export interface NetworkEdge {
  id: string
  source: string
  target: string
  label: string
  [key: string]: unknown
}

export interface NetworkResponse {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

export function useCaseNetwork(caseId?: string) {
  return useQuery<NetworkResponse>({
    queryKey: ['case-network', caseId],
    queryFn: async () => {
      if (!caseId) throw new Error('Case ID is required')
      const response = await fetch(`/cases/${caseId}/network`)
      if (!response.ok) {
        throw new Error(`Failed to fetch case network: ${response.statusText}`)
      }
      return response.json()
    },
    enabled: !!caseId,
    staleTime: 0,
  })
}
