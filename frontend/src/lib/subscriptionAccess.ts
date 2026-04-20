/**
 * Normalizes /billing/subscription/current API payloads (cached DB row or Stripe-shaped).
 */
export function hasActiveSubscription(payload: unknown): boolean {
  if (!payload || typeof payload !== 'object') return false
  const data = payload as { success?: boolean; subscription?: { status?: string } | null }
  if (data.success === false) return false
  const sub = data.subscription
  if (!sub || typeof sub !== 'object') return false
  const status = String((sub as { status?: string }).status || '')
    .trim()
    .toLowerCase()
  return status === 'active' || status === 'trialing'
}

export function isSubscriptionGateEnabled(): boolean {
  if (import.meta.env.VITE_DISABLE_SUBSCRIPTION_GATE === 'true') return false
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_SUBSCRIPTION_GATE !== 'true') return false
  return true
}
