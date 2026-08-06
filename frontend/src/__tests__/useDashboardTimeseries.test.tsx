import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useDashboardTimeseries } from '../hooks/useDashboardTimeseries'

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
    getDashboardTimeseries: vi.fn(),
  },
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useDashboardTimeseries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClientMock.getDashboardTimeseries.mockResolvedValue({
      success: true,
      data: {
        timeseries: [{ day: '2025-01-01', leads: 1, emails: 2, responses: 0, revenue: 0 }],
        summary: {
          leads: { change_pct: 1, positive: true },
          emails: { change_pct: 2, positive: true },
          responses: { change_pct: null, positive: true },
          revenue: { change_pct: null, positive: true },
        },
      },
    })
  })

  it('dedupes concurrent mounts onto one network call', async () => {
    const Wrap = createWrapper()
    const { result: a } = renderHook(() => useDashboardTimeseries('week'), { wrapper: Wrap })
    const { result: b } = renderHook(() => useDashboardTimeseries('week'), { wrapper: Wrap })

    await waitFor(() => {
      expect(a.current.loading).toBe(false)
      expect(b.current.loading).toBe(false)
    })

    expect(apiClientMock.getDashboardTimeseries).toHaveBeenCalledTimes(1)
    expect(a.current.data).toHaveLength(1)
    expect(b.current.data).toHaveLength(1)
  })
})
