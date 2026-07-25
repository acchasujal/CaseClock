import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import type { DeadlineMonitorStatusResponse } from '@shared/contracts/api'

export function useDeadlineMonitor() {
  return useQuery<DeadlineMonitorStatusResponse>({
    queryKey: ['deadline-monitor-status'],
    queryFn: () => apiFetch<DeadlineMonitorStatusResponse>('/api/v1/system/deadline-monitor/status'),
    refetchInterval: 30000,
    staleTime: 10000,
  })
}
