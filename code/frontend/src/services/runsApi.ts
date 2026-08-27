import { request } from './httpClient'
import type { RunFull, RunListItem, RunResume } from '@/types/api'

export const runsApi = {
  list(signal?: AbortSignal) {
    return request<{ total: number; runs: RunListItem[] }>('/runs', { signal })
  },

  resume(runId: string, signal?: AbortSignal) {
    return request<RunResume>(`/runs/${runId}?dataset=resume`, { signal })
  },

  full(runId: string, signal?: AbortSignal) {
    return request<RunFull>(`/runs/${runId}?dataset=full`, { signal })
  },

  result(runId: string, signal?: AbortSignal) {
    return request<Record<string, unknown>>(`/runs/${runId}/result`, { signal })
  },
}
