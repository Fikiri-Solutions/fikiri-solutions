import { describe, expect, it } from 'vitest'
import { shouldShowPlatformAdminNav } from '../hooks/usePlatformAdmin'

describe('shouldShowPlatformAdminNav', () => {
  it('shows Admin for a confirmed platform operator', () => {
    expect(
      shouldShowPlatformAdminNav({
        loading: false,
        isPlatformAdmin: true,
        failed: false,
      })
    ).toBe(true)
  })

  it('hides Admin for a normal tenant admin (not platform operator)', () => {
    expect(
      shouldShowPlatformAdminNav({
        loading: false,
        isPlatformAdmin: false,
        failed: false,
      })
    ).toBe(false)
  })

  it('hides Admin while operator status is loading', () => {
    expect(
      shouldShowPlatformAdminNav({
        loading: true,
        isPlatformAdmin: true,
        failed: false,
      })
    ).toBe(false)
  })

  it('hides Admin on forbidden/failed platform-me responses', () => {
    expect(
      shouldShowPlatformAdminNav({
        loading: false,
        isPlatformAdmin: false,
        failed: true,
      })
    ).toBe(false)
    expect(
      shouldShowPlatformAdminNav({
        loading: false,
        isPlatformAdmin: true,
        failed: true,
      })
    ).toBe(false)
  })

  it('a platform-me failure does not imply Admin visibility (dashboard nav unaffected)', () => {
    // Failure → hide Admin; callers still render the rest of dashboardNav independently.
    const showAdmin = shouldShowPlatformAdminNav({
      loading: false,
      isPlatformAdmin: false,
      failed: true,
    })
    expect(showAdmin).toBe(false)
  })
})
