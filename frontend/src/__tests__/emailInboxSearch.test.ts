import { describe, it, expect, vi, beforeEach } from 'vitest'

const getMock = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: getMock,
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
    post: vi.fn(),
  },
}))

vi.mock('../config', () => ({
  config: {
    apiUrl: 'http://localhost:5000/api',
  },
}))

vi.mock('../utils/cacheInvalidation', () => ({
  CacheInvalidationManager: {
    getInstance: () => ({
      invalidate: vi.fn(),
      getCacheHeaders: () => ({}),
    }),
  },
}))

describe('apiClient.getEmails inbox search + pagination', () => {
  beforeEach(() => {
    vi.resetModules()
    getMock.mockReset()
    localStorage.setItem('fikiri-user-id', '1')
    getMock.mockResolvedValue({
      data: {
        data: {
          emails: [{ id: 'm1', subject: 'FAU', from: 'a@fau.edu', snippet: 'x', unread: true }],
          source: 'gmail_api',
          pagination: { has_more: true, next_page_token: 'tok-next' },
        },
      },
    })
  })

  it('sends q to backend (server search), not client-only', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getEmails({
      filter: 'all',
      limit: 50,
      use_synced: false,
      q: 'Florida Atlantic University',
    })

    expect(getMock).toHaveBeenCalledWith('/email/messages', {
      params: expect.objectContaining({
        q: 'Florida Atlantic University',
        use_synced: false,
        filter: 'all',
        limit: 50,
        user_id: 1,
      }),
    })
  })

  it('sends page_token for load more (not a higher limit only)', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getEmails({
      filter: 'unread',
      limit: 50,
      use_synced: false,
      q: 'Florida Atlantic University',
      page_token: 'tok-next',
    })

    expect(getMock).toHaveBeenCalledWith('/email/messages', {
      params: expect.objectContaining({
        page_token: 'tok-next',
        q: 'Florida Atlantic University',
        filter: 'unread',
        limit: 50,
      }),
    })
  })

  it('defaults use_synced true when omitted (synced mode safe path)', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getEmails({ q: 'FAU' })

    expect(getMock).toHaveBeenCalledWith('/email/messages', {
      params: expect.objectContaining({
        q: 'FAU',
        use_synced: true,
      }),
    })
  })
})

describe('useDebouncedValue', () => {
  it('clears debounced value when search input cleared', async () => {
    vi.useFakeTimers()
    const { useDebouncedValue } = await import('../hooks/useDebouncedValue')
    const { renderHook, act } = await import('@testing-library/react')

    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebouncedValue(value, 400),
      { initialProps: { value: 'Florida Atlantic University' } }
    )

    act(() => {
      vi.advanceTimersByTime(400)
    })
    expect(result.current).toBe('Florida Atlantic University')

    rerender({ value: '' })
    act(() => {
      vi.advanceTimersByTime(400)
    })
    expect(result.current).toBe('')

    vi.useRealTimers()
  })
})
