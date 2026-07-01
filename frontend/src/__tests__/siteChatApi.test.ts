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
})
