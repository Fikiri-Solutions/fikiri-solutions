import { describe, expect, it } from 'vitest'
import { handoffPath, siteChatApiBase } from '../services/siteChatApi'

describe('siteChatApi helpers', () => {
  it('builds site chat API base under /api/site/chat', () => {
    expect(siteChatApiBase()).toMatch(/\/api\/site\/chat$/)
  })

  it('resolves handoff path when applicable', () => {
    expect(
      handoffPath({ applicable: true, secondary: '/intake', handoff_type: 'intake' })
    ).toBe('/intake')
    expect(handoffPath({ applicable: false, secondary: '/contact' })).toBeNull()
  })

  it('prefills intake handoff from chat slots', () => {
    const path = handoffPath(
      { applicable: true, secondary: '/intake', handoff_type: 'intake' },
      { active: false, complete: true, slots: { industry: 'dental', contact_email: 'a@b.co' } }
    )
    expect(path).toContain('/intake?')
    expect(path).toContain('industry=dental')
    expect(path).toContain('email=a%40b.co')
  })
})
