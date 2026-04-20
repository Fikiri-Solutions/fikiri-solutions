import { describe, it, expect } from 'vitest'
import { hasActiveSubscription } from '../lib/subscriptionAccess'

describe('hasActiveSubscription', () => {
  it('returns false for null, non-objects, or success false', () => {
    expect(hasActiveSubscription(null)).toBe(false)
    expect(hasActiveSubscription(undefined)).toBe(false)
    expect(hasActiveSubscription('x')).toBe(false)
    expect(hasActiveSubscription({ success: false, subscription: { status: 'active' } })).toBe(false)
  })

  it('returns false when subscription missing or null', () => {
    expect(hasActiveSubscription({ success: true })).toBe(false)
    expect(hasActiveSubscription({ success: true, subscription: null })).toBe(false)
  })

  it('returns true only for active or trialing', () => {
    expect(hasActiveSubscription({ success: true, subscription: { status: 'active' } })).toBe(true)
    expect(hasActiveSubscription({ success: true, subscription: { status: 'trialing' } })).toBe(true)
    expect(hasActiveSubscription({ success: true, subscription: { status: 'ACTIVE' } })).toBe(true)
    expect(hasActiveSubscription({ subscription: { status: 'active' } })).toBe(true)
  })

  it('returns false for other statuses', () => {
    expect(hasActiveSubscription({ success: true, subscription: { status: 'canceled' } })).toBe(false)
    expect(hasActiveSubscription({ success: true, subscription: { status: 'past_due' } })).toBe(false)
    expect(hasActiveSubscription({ success: true, subscription: { status: 'incomplete' } })).toBe(false)
  })
})
