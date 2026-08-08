import { describe, expect, it } from 'vitest'
import { safeInternalPath } from '../utils/safeInternalPath'

describe('safeInternalPath', () => {
  it('allows internal absolute paths', () => {
    expect(safeInternalPath('/onboarding')).toBe('/onboarding')
    expect(safeInternalPath('/dashboard')).toBe('/dashboard')
    expect(safeInternalPath('/onboarding?x=1')).toBe('/onboarding?x=1')
  })

  it('rejects open redirects and auth loops', () => {
    expect(safeInternalPath('https://evil.example')).toBeNull()
    expect(safeInternalPath('//evil.example')).toBeNull()
    expect(safeInternalPath('/login')).toBeNull()
    expect(safeInternalPath('/signup')).toBeNull()
    expect(safeInternalPath(null)).toBeNull()
    expect(safeInternalPath('')).toBeNull()
  })
})
