import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  trackFeatureOpened,
  trackProductEvents,
  _resetProductAnalyticsClientForTests,
} from '../services/productAnalytics'

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getProductAnalyticsStatus: vi.fn(),
    postProductAnalyticsEvents: vi.fn(),
  },
}))

import { apiClient } from '../services/apiClient'

describe('productAnalytics client', () => {
  beforeEach(() => {
    _resetProductAnalyticsClientForTests()
    vi.clearAllMocks()
    ;(apiClient.getProductAnalyticsStatus as any).mockResolvedValue({
      analytics_enabled: true,
      accessibility_signals_enabled: false,
      impersonating: false,
    })
    ;(apiClient.postProductAnalyticsEvents as any).mockResolvedValue({ accepted: 1 })
    Object.defineProperty(window, 'location', {
      value: { pathname: '/dashboard' },
      writable: true,
    })
  })

  it('dedupes feature.opened within the short window', async () => {
    trackFeatureOpened('crm')
    trackFeatureOpened('crm')
    await new Promise((r) => setTimeout(r, 30))
    expect(apiClient.postProductAnalyticsEvents).toHaveBeenCalledTimes(1)
  })

  it('skips admin paths', async () => {
    Object.defineProperty(window, 'location', {
      value: { pathname: '/admin/tenants' },
      writable: true,
    })
    await trackProductEvents([{ event_name: 'session.started' }])
    expect(apiClient.postProductAnalyticsEvents).not.toHaveBeenCalled()
  })

  it('skips when impersonating', async () => {
    ;(apiClient.getProductAnalyticsStatus as any).mockResolvedValue({
      analytics_enabled: true,
      accessibility_signals_enabled: false,
      impersonating: true,
    })
    await trackProductEvents([{ event_name: 'session.started' }])
    expect(apiClient.postProductAnalyticsEvents).not.toHaveBeenCalled()
  })

  it('skips when analytics disabled', async () => {
    ;(apiClient.getProductAnalyticsStatus as any).mockResolvedValue({
      analytics_enabled: false,
      accessibility_signals_enabled: false,
      impersonating: false,
    })
    await trackProductEvents([{ event_name: 'feature.opened', properties: { feature_key: 'crm' } }])
    expect(apiClient.postProductAnalyticsEvents).not.toHaveBeenCalled()
  })
})
