import { describe, expect, it, vi, afterEach } from 'vitest'

describe('demoSafety', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('demo safe mode is off by default', async () => {
    vi.stubEnv('VITE_DEMO_SAFE_MODE', '')
    const { isDemoSafeMode, isNavHiddenInDemoSafeMode } = await import('../lib/demoSafety')
    expect(isDemoSafeMode()).toBe(false)
    expect(isNavHiddenInDemoSafeMode('/ai')).toBe(false)
  })

  it('demo safe mode hides unstable nav items', async () => {
    vi.stubEnv('VITE_DEMO_SAFE_MODE', 'true')
    const { isDemoSafeMode, isNavHiddenInDemoSafeMode } = await import('../lib/demoSafety')
    expect(isDemoSafeMode()).toBe(true)
    expect(isNavHiddenInDemoSafeMode('/crm')).toBe(false)
    expect(isNavHiddenInDemoSafeMode('/ai')).toBe(true)
    expect(isNavHiddenInDemoSafeMode('/ai/chatbot-builder')).toBe(true)
    expect(isNavHiddenInDemoSafeMode('/services')).toBe(true)
  })

  it('email AI requires explicit enable flag', async () => {
    vi.stubEnv('VITE_DEMO_EMAIL_AI_ENABLED', '')
    const { isEmailAiDemoEnabled } = await import('../lib/demoSafety')
    expect(isEmailAiDemoEnabled()).toBe(false)
    vi.stubEnv('VITE_DEMO_EMAIL_AI_ENABLED', 'true')
    const mod = await import('../lib/demoSafety')
    expect(mod.isEmailAiDemoEnabled()).toBe(true)
  })
})
