import { describe, expect, it } from 'vitest'
import {
  getMobileBottomNavItems,
  getDashboardSidebarNav,
  isDashboardNavItemActive,
} from '../navigation/dashboardNav'

describe('dashboardNav', () => {
  it('isDashboardNavItemActive handles nested app routes', () => {
    expect(isDashboardNavItemActive('/ai/chatbot-builder', '/ai')).toBe(true)
    expect(isDashboardNavItemActive('/assistant', '/ai')).toBe(true)
    expect(isDashboardNavItemActive('/integrations/outlook', '/integrations/gmail')).toBe(true)
    expect(isDashboardNavItemActive('/onboarding/2', '/onboarding')).toBe(true)
    expect(isDashboardNavItemActive('/dashboard', '/home')).toBe(false)
    expect(isDashboardNavItemActive('/home', '/dashboard')).toBe(true)
    expect(isDashboardNavItemActive('/industry', '/analytics')).toBe(true)
  })

  it('getMobileBottomNavItems swaps analytics for onboarding when setup incomplete', () => {
    const done = getMobileBottomNavItems({ onboarding_completed: true })
    expect(done.map((i) => i.href)).toContain('/analytics')
    expect(done.map((i) => i.href)).not.toContain('/onboarding')

    const pending = getMobileBottomNavItems({ onboarding_completed: false })
    expect(pending.map((i) => i.href)).toContain('/onboarding')
    expect(pending.map((i) => i.href)).not.toContain('/analytics')
    expect(pending).toHaveLength(6)
  })

  it('getDashboardSidebarNav prepends onboarding when incomplete', () => {
    const pending = getDashboardSidebarNav({ onboarding_completed: false })
    expect(pending[0]?.href).toBe('/onboarding')
    const done = getDashboardSidebarNav({ onboarding_completed: true })
    expect(done.find((i) => i.href === '/onboarding')).toBeUndefined()
  })

  it('getMobileBottomNavItems uses default tab bar when user is null (auth loading)', () => {
    const nullUser = getMobileBottomNavItems(null)
    const undefinedUser = getMobileBottomNavItems(undefined)
    expect(nullUser).toHaveLength(6)
    expect(undefinedUser.map((i) => i.href)).toEqual(nullUser.map((i) => i.href))
    expect(nullUser.map((i) => i.href)).toContain('/analytics')
    expect(nullUser.map((i) => i.href)).not.toContain('/onboarding')
  })

  it('sidebar nav items have unique hrefs', () => {
    for (const completed of [true, false]) {
      const items = getDashboardSidebarNav({ onboarding_completed: completed })
      const hrefs = items.map((i) => i.href)
      expect(new Set(hrefs).size, `duplicate href when onboarding_completed=${completed}`).toBe(hrefs.length)
    }
  })
})
