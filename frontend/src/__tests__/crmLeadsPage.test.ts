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

describe('apiClient.getLeadsPage', () => {
  beforeEach(() => {
    vi.resetModules()
    getMock.mockReset()
    localStorage.setItem('fikiri-user-id', '1')
    getMock.mockResolvedValue({
      data: {
        data: {
          leads: [
            {
              id: 1,
              name: 'Jane Smith',
              email: 'jane@example.com',
              stage: 'contacted',
              score: 42,
            },
          ],
          pagination: {
            total_count: 42,
            returned_count: 1,
            limit: 50,
            offset: 25,
            has_more: true,
          },
        },
      },
    })
  })

  it('sends q, stage, limit, offset, sort, and direction', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getLeadsPage({
      q: 'jane',
      stage: 'contacted',
      limit: 50,
      offset: 25,
      sort: 'score',
      direction: 'desc',
    })

    expect(getMock).toHaveBeenCalledWith('/crm/leads', {
      params: {
        user_id: 1,
        q: 'jane',
        stage: 'contacted',
        limit: 50,
        offset: 25,
        sort: 'score',
        direction: 'desc',
      },
    })
  })

  it('omits user_id when fikiri-user-id is not stored', async () => {
    localStorage.removeItem('fikiri-user-id')
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getLeadsPage({ limit: 50, offset: 0 })

    expect(getMock).toHaveBeenCalledWith('/crm/leads', {
      params: {
        limit: 50,
        offset: 0,
      },
    })
  })

  it('omits empty q and stage all', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getLeadsPage({ q: '   ', stage: 'all', limit: 50, offset: 0 })

    expect(getMock).toHaveBeenCalledWith('/crm/leads', {
      params: {
        user_id: 1,
        limit: 50,
        offset: 0,
      },
    })
  })

  it('maps pagination metadata and lead rows', async () => {
    const { apiClient } = await import('../services/apiClient')
    const result = await apiClient.getLeadsPage({ limit: 50, offset: 25 })

    expect(result.leads).toHaveLength(1)
    expect(result.leads[0].name).toBe('Jane Smith')
    expect(result.pagination).toEqual({
      total_count: 42,
      returned_count: 1,
      limit: 50,
      offset: 25,
      has_more: true,
    })
  })

  it('derives offset from page when offset is omitted', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.getLeadsPage({ page: 3, limit: 10 })

    expect(getMock).toHaveBeenCalledWith('/crm/leads', {
      params: expect.objectContaining({
        limit: 10,
        offset: 20,
      }),
    })
  })
})
