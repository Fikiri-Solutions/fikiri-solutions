/**
 * Minimal product analytics client.
 * - Skips /admin surfaces and impersonation.
 * - Dedupes feature.opened per feature within a short window.
 * - Never sends identity or prohibited fields.
 */

import { apiClient } from './apiClient'

type AnalyticsEvent = {
  event_name: string
  event_source?: 'client'
  properties?: Record<string, string | number | boolean>
  client_timestamp?: string
}

const DEDUPE_MS = 15_000
const featureOpenSeen = new Map<string, number>()

let cachedStatus: {
  analytics_enabled: boolean
  accessibility_signals_enabled: boolean
  impersonating: boolean
} | null = null

function isAdminPath(): boolean {
  if (typeof window === 'undefined') return true
  return window.location.pathname.startsWith('/admin')
}

async function getStatus() {
  if (cachedStatus) return cachedStatus
  try {
    cachedStatus = await apiClient.getProductAnalyticsStatus()
  } catch {
    cachedStatus = {
      analytics_enabled: false,
      accessibility_signals_enabled: false,
      impersonating: false,
    }
  }
  return cachedStatus
}

export async function trackProductEvents(events: AnalyticsEvent[], surface?: string): Promise<void> {
  if (!events.length) return
  if (isAdminPath() || surface === 'admin') return
  const status = await getStatus()
  if (!status.analytics_enabled || status.impersonating) return
  try {
    await apiClient.postProductAnalyticsEvents({
      surface: surface || 'app',
      events: events.map((e) => ({
        event_name: e.event_name,
        event_source: 'client',
        properties: e.properties || {},
        client_timestamp: e.client_timestamp || new Date().toISOString(),
      })),
    })
  } catch {
    // Analytics must never break product UX
  }
}

export function trackFeatureOpened(featureKey: string): void {
  if (isAdminPath()) return
  const now = Date.now()
  const last = featureOpenSeen.get(featureKey) || 0
  if (now - last < DEDUPE_MS) return
  featureOpenSeen.set(featureKey, now)
  void trackProductEvents([
    {
      event_name: 'feature.opened',
      properties: { feature_key: featureKey },
    },
  ])
}

export function trackSessionStarted(): void {
  if (isAdminPath()) return
  const key = 'session'
  const now = Date.now()
  const last = featureOpenSeen.get(key) || 0
  // Coarse: at most one session.started per 30 minutes in this tab
  if (now - last < 30 * 60 * 1000) return
  featureOpenSeen.set(key, now)
  void trackProductEvents([{ event_name: 'session.started', properties: {} }])
}

/** Test helper */
export function _resetProductAnalyticsClientForTests(): void {
  cachedStatus = null
  featureOpenSeen.clear()
}
