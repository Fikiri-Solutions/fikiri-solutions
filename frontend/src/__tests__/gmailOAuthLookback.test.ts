import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GMAIL_LOOKBACK_STORAGE_KEY } from '../utils/gmailLookbackStorage'

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

describe('apiClient.startGmailOAuth lookback param', () => {
  beforeEach(() => {
    vi.resetModules()
    getMock.mockReset()
    getMock.mockResolvedValue({ data: { url: 'https://accounts.google.com/o/oauth2' } })
    localStorage.clear()
  })

  it('sends lookback query param when preset is provided', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.startGmailOAuth('/integrations/gmail', '1y')

    expect(getMock).toHaveBeenCalledWith('/oauth/gmail/start', {
      params: { redirect: '/integrations/gmail', lookback: '1y' },
    })
  })

  it('omits lookback when not provided', async () => {
    const { apiClient } = await import('../services/apiClient')
    await apiClient.startGmailOAuth('/onboarding/2')

    expect(getMock).toHaveBeenCalledWith('/oauth/gmail/start', {
      params: { redirect: '/onboarding/2' },
    })
  })
})

describe('loadGmailLookbackId', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('reads stored preset from localStorage', async () => {
    localStorage.setItem(GMAIL_LOOKBACK_STORAGE_KEY, '2y')
    const { loadGmailLookbackId } = await import('../utils/gmailLookbackStorage')
    expect(loadGmailLookbackId()).toBe('2y')
  })

  it('falls back to 90d when storage is missing or invalid', async () => {
    const { loadGmailLookbackId } = await import('../utils/gmailLookbackStorage')
    expect(loadGmailLookbackId()).toBe('90d')
    localStorage.setItem(GMAIL_LOOKBACK_STORAGE_KEY, 'invalid')
    expect(loadGmailLookbackId()).toBe('90d')
  })
})
