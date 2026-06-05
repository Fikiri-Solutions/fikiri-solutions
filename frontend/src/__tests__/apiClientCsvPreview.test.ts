import { beforeEach, describe, expect, it, vi } from 'vitest'

const postMock = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: postMock,
      get: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

vi.mock('../config', () => ({
  config: { apiUrl: 'http://localhost:5000/api' },
}))

vi.mock('../utils/cacheInvalidation', () => ({
  CacheInvalidationManager: {
    getInstance: () => ({
      invalidate: vi.fn(),
      getCacheHeaders: () => ({}),
    }),
  },
}))

describe('apiClient.previewLeadsCsv', () => {
  beforeEach(() => {
    vi.resetModules()
    postMock.mockReset()
  })

  it('preserves backend total_rows when summary does not include total', async () => {
    postMock.mockResolvedValue({
      data: {
        data: {
          total_rows: 750,
          summary: { ok: 498, duplicate: 2, invalid: 250 },
          rows: [{ row: 2, email: 'a@example.com', name: 'Ada', status: 'ok' }],
        },
      },
    })

    const { apiClient } = await import('../services/apiClient')
    const file = new File(['email,name\na@example.com,Ada'], 'leads.csv', { type: 'text/csv' })

    const result = await apiClient.previewLeadsCsv(file)

    expect(postMock).toHaveBeenCalledWith('/crm/leads/import/csv/preview', expect.any(FormData))
    expect(result.summary).toEqual({ ok: 498, duplicate: 2, invalid: 250, total: 750 })
  })
})
