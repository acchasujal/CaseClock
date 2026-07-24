import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'

export interface StationRanking {
  station_name: string
  total: number
  critical: number
}

export interface DistrictRollupResponse {
  total_cases: number
  red_clocks: number
  amber_clocks: number
  stale_dependencies: number
  station_rankings: StationRanking[]
}

export function useRollup(district: string) {
  return useQuery<DistrictRollupResponse>({
    queryKey: ['district-rollup', district],
    queryFn: () => apiFetch<DistrictRollupResponse>(`/rollup/${encodeURIComponent(district)}`),
    enabled: Boolean(district),
    staleTime: 0,
  })
}
