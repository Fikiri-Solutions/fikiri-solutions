import { describe, it, expect } from 'vitest'
import {
  SUBSCRIPTION_SIGNUP_STEPS,
  getSubscriptionSignupSteps,
} from '../content/subscriptionSignupInstructions'

describe('getSubscriptionSignupSteps', () => {
  it('returns five steps for gate and billing', () => {
    expect(getSubscriptionSignupSteps('gate').length).toBe(5)
    expect(getSubscriptionSignupSteps('billing').length).toBe(5)
  })

  it('gate first step matches canonical open-billing copy', () => {
    expect(getSubscriptionSignupSteps('gate')[0].heading).toBe(SUBSCRIPTION_SIGNUP_STEPS[0].heading)
  })

  it('billing first step is tailored for already being on /billing', () => {
    const first = getSubscriptionSignupSteps('billing')[0]
    expect(first.heading).toBe('You are on Billing')
    expect(first.detail).toContain('Available Plans')
    expect(first.detail.toLowerCase()).not.toMatch(/go to billing/i)
  })

  it('billing variant shares steps 2–5 with gate', () => {
    const gate = getSubscriptionSignupSteps('gate')
    const billing = getSubscriptionSignupSteps('billing')
    expect(billing.slice(1)).toEqual(gate.slice(1))
  })
})
