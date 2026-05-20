import { describe, it, expect, vi, beforeEach } from 'vitest'

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
    post: vi.fn(),
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

describe('apiClient.previewChatbotQuery', () => {
  beforeEach(() => {
    vi.resetModules()
    postMock.mockReset()
  })

  it('posts to /chatbot/preview-query with query body', async () => {
    postMock.mockResolvedValue({
      data: {
        success: true,
        answer: 'ok',
        confidence: 1,
        fallback_used: false,
        sources: [],
        config_applied: true,
      },
    })

    const { apiClient } = await import('../services/apiClient')
    const result = await apiClient.previewChatbotQuery('What are your hours?')

    expect(postMock).toHaveBeenCalledWith('/chatbot/preview-query', {
      query: 'What are your hours?',
    })
    expect(result.answer).toBe('ok')
  })

  it('includes conversation_id when provided', async () => {
    postMock.mockResolvedValue({
      data: {
        success: true,
        answer: 'follow-up',
        confidence: 0.9,
        fallback_used: false,
        sources: [],
        config_applied: true,
      },
    })

    const { apiClient } = await import('../services/apiClient')
    await apiClient.previewChatbotQuery('follow up', 'conv-123')

    expect(postMock).toHaveBeenCalledWith('/chatbot/preview-query', {
      query: 'follow up',
      conversation_id: 'conv-123',
    })
  })
})
