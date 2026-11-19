import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  _resetSiteMarketingAnalyticsForTests,
  trackChatbotOpened,
  trackIntakeStarted,
  trackIntakeStepViewed,
} from '../services/siteMarketingAnalytics'

describe('siteMarketingAnalytics', () => {
  beforeEach(() => {
    _resetSiteMarketingAnalyticsForTests()
    vi.restoreAllMocks()
    sessionStorage.clear()
  })

  it('posts bounded intake events without PII fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)

    trackIntakeStarted('site_chatbot')
    trackIntakeStepViewed('services')
    trackIntakeStepViewed('services') // deduped client-side
    trackChatbotOpened()

    await vi.waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3))

    for (const call of fetchMock.mock.calls) {
      const init = call[1] as RequestInit
      const body = JSON.parse(String(init.body))
      expect(body.session_ref).toMatch(/^[A-Za-z0-9_-]+$/)
      for (const event of body.events) {
        expect(JSON.stringify(event)).not.toMatch(/email|phone|@/i)
      }
    }
  })
})
