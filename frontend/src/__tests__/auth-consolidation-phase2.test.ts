import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../store/auth'

const protectedFiles = [
  '../components/PrivacySettings.tsx?raw',
  '../components/IndustryAutomation.tsx?raw',
  '../components/SyncProgress.tsx?raw',
]

const touchedFiles = [
  ...protectedFiles,
  '../pages/Signup.tsx?raw',
  '../pages/Login.tsx?raw',
]

async function source(path: string): Promise<string> {
  const sources: Record<string, () => Promise<{ default: string }>> = {
    '../components/PrivacySettings.tsx?raw': () => import('../components/PrivacySettings.tsx?raw'),
    '../components/IndustryAutomation.tsx?raw': () => import('../components/IndustryAutomation.tsx?raw'),
    '../components/SyncProgress.tsx?raw': () => import('../components/SyncProgress.tsx?raw'),
    '../pages/Signup.tsx?raw': () => import('../pages/Signup.tsx?raw'),
    '../pages/Login.tsx?raw': () => import('../pages/Login.tsx?raw'),
  }
  return (await sources[path]()).default
}

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  )
}

describe('frontend auth consolidation phase 2', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuth.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('PrivacySettings protected calls use the shared API helper', async () => {
    const text = await source('../components/PrivacySettings.tsx?raw')
    expect(text).toContain("import { ApiError, apiGet, apiPost, apiPut } from '../lib/api'")
    expect(text).toContain('apiGet<PrivacySettings>(`/privacy/settings')
    expect(text).toContain('apiGet<DataSummary>(`/privacy/data-summary')
    expect(text).toContain('apiGet<{ consents: PrivacyConsent[] }>(`/privacy/consents')
    expect(text).toContain("apiPut<{ settings: PrivacySettings }>('/privacy/settings'")
    expect(text).toContain("apiPost<{ total_deleted: number }>('/privacy/cleanup'")
    expect(text).toContain("apiPost('/privacy/delete'")
    expect(text).not.toContain('fetch(')
  })

  it('IndustryAutomation protected AI call uses the shared API helper', async () => {
    const text = await source('../components/IndustryAutomation.tsx?raw')
    expect(text).toContain("import { ApiError, apiPost } from '../lib/api'")
    expect(text).toContain("apiPost<any>('/ai/chat'")
    expect(text).not.toContain('fetch(')
  })

  it('SyncProgress protected polling uses the shared API helper', async () => {
    const text = await source('../components/SyncProgress.tsx?raw')
    expect(text).toContain("import { apiGet } from '../lib/api'")
    expect(text).toContain('apiGet<{ progress: any }>(`/onboarding/status')
    expect(text).not.toContain('fetch(')
  })

  it('touched files do not use hardcoded production backend URLs', async () => {
    for (const path of touchedFiles) {
      expect(await source(path)).not.toContain('https://fikirisolutions.onrender.com/api')
    }
  })

  it('shared helper attaches bearer auth from Zustand and omits cookie credentials', async () => {
    useAuth.getState().login({
      id: 1,
      email: 'user@example.com',
      name: 'Test User',
      role: 'user',
      onboarding_completed: true,
      onboarding_step: 4,
    }, 'access-token', 'refresh-token')
    vi.mocked(fetch).mockResolvedValueOnce(await jsonResponse({
      success: true,
      data: { ok: true },
    }))

    await apiGet('/privacy/settings?user_id=1')

    const init = vi.mocked(fetch).mock.calls[0][1]
    const headers = init?.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer access-token')
    expect(init?.credentials).toBeUndefined()
  })

  it('shared helper methods serialize protected write bodies', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(await jsonResponse({ success: true, data: { ok: true } }))
      .mockResolvedValueOnce(await jsonResponse({ success: true, data: { ok: true } }))

    await apiPost('/privacy/cleanup', { user_id: 1 })
    await apiPut('/privacy/settings', { user_id: 1, analytics_tracking_enabled: false })

    expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBe(JSON.stringify({ user_id: 1 }))
    expect(vi.mocked(fetch).mock.calls[1][1]?.body).toBe(JSON.stringify({
      user_id: 1,
      analytics_tracking_enabled: false,
    }))
  })

  it('no plaintext password storage is reintroduced', async () => {
    const text = await source('../pages/Login.tsx?raw')
    expect(text).not.toContain("setItem('fikiri-remember-password'")
    expect(text).not.toContain('setItem("fikiri-remember-password"')
  })
})
