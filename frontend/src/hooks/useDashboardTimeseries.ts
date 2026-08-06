import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'

interface TimeseriesData {
  day: string
  leads: number
  emails: number
  responses: number
  revenue: number
}

interface SummaryData {
  leads: { change_pct: number | null; positive: boolean }
  emails: { change_pct: number | null; positive: boolean }
  responses: { change_pct: number | null; positive: boolean }
  revenue: { change_pct: number | null; positive: boolean }
}

const EMPTY_SUMMARY: SummaryData = {
  leads: { change_pct: null, positive: true },
  emails: { change_pct: null, positive: true },
  responses: { change_pct: null, positive: true },
  revenue: { change_pct: null, positive: true },
}

/** Shared React Query key — must match useDashboardData / GettingStartedWizard. */
export function dashboardTimeseriesQueryKey(period: 'week' | 'month' | 'quarter' = 'week') {
  return ['dashboard', 'timeseries', period] as const
}

/**
 * Dashboard timeseries via shared React Query cache (dedupes Strict Mode + sibling mounts).
 */
export function useDashboardTimeseries(period: 'week' | 'month' | 'quarter' = 'week') {
  const query = useQuery({
    queryKey: dashboardTimeseriesQueryKey(period),
    queryFn: () => apiClient.getDashboardTimeseries(undefined, period),
    staleTime: 60_000,
    refetchInterval: 300_000,
    retry: 2,
  })

  const payload = query.data
  const raw = payload?.data?.timeseries ?? payload?.timeseries ?? []
  const data: TimeseriesData[] = Array.isArray(raw) ? raw : []
  const summary: SummaryData = payload?.data?.summary ?? payload?.summary ?? EMPTY_SUMMARY

  return {
    data,
    summary,
    loading: query.isLoading,
    error: query.error
      ? query.error instanceof Error
        ? query.error.message
        : 'Failed to fetch data'
      : null,
    refetch: query.refetch,
  }
}
