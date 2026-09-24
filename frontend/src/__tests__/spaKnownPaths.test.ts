import { describe, expect, it } from 'vitest'
import {
  isKnownSpaPath,
  isStaticAssetPath,
  normalizePathname,
} from '../lib/spaKnownPaths'

describe('spaKnownPaths', () => {
  it('normalizes trailing slashes', () => {
    expect(normalizePathname('/about/')).toBe('/about')
    expect(normalizePathname('/')).toBe('/')
  })

  it('recognizes public and app SPA routes', () => {
    expect(isKnownSpaPath('/')).toBe(true)
    expect(isKnownSpaPath('/privacy')).toBe(true)
    expect(isKnownSpaPath('/contact')).toBe(true)
    expect(isKnownSpaPath('/dashboard')).toBe(true)
    expect(isKnownSpaPath('/onboarding/2')).toBe(true)
    expect(isKnownSpaPath('/inbox')).toBe(true)
    expect(isKnownSpaPath('/inbox/thread/1')).toBe(true)
    expect(isKnownSpaPath('/admin/tenants/abc')).toBe(true)
    expect(isKnownSpaPath('/integrations/gmail')).toBe(true)
  })

  it('rejects unknown paths', () => {
    expect(isKnownSpaPath('/this-page-should-not-exist-829173')).toBe(false)
    expect(isKnownSpaPath('/privacy-policy')).toBe(false)
    expect(isKnownSpaPath('/random/deep/path')).toBe(false)
  })

  it('identifies static assets', () => {
    expect(isStaticAssetPath('/assets/index.js')).toBe(true)
    expect(isStaticAssetPath('/brand/hero/fikiri-hero-mobile.webp')).toBe(true)
    expect(isStaticAssetPath('/robots.txt')).toBe(true)
    expect(isStaticAssetPath('/integrations/universal/fikiri-sdk.js')).toBe(true)
    expect(isStaticAssetPath('/contact')).toBe(false)
  })
})
