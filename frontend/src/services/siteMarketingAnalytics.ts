/**
 * Anonymous public marketing funnel events (intake + chatbot).
 * First-party collector — Vercel custom events require Pro/Enterprise.
 * Never sends names, emails, phones, free text, or chat content.
 */

import { config } from '../config'

export type SiteMarketingEventName =
  | 'intake_started'
  | 'intake_step_viewed'
  | 'intake_submitted'
  | 'booking_clicked'
  | 'chatbot_opened'
  | 'chatbot_first_message'
  | 'chatbot_fallback'
  | 'chatbot_handoff'

type EventProps = Record<string, string | number | boolean>

type QueuedEvent = {
  event_name: SiteMarketingEventName
  properties?: EventProps
  dedupe_key?: string
  client_timestamp: string
}

const SESSION_KEY = 'fikiri_site_analytics_session'
const EVENTS_URL = `${config.apiUrl.replace(/\/+$/, '')}/site/events`
const flushSeen = new Set<string>()

function makeSessionRef(): string {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID().replace(/-/g, '').slice(0, 32)
    }
  } catch {
    /* ignore */
  }
  return `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`
}

export function getSiteAnalyticsSessionRef(): string {
  if (typeof window === 'undefined') return 'server'
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY)
    if (existing && /^[A-Za-z0-9_-]{8,64}$/.test(existing)) return existing
    const next = makeSessionRef()
    window.sessionStorage.setItem(SESSION_KEY, next)
    return next
  } catch {
    return makeSessionRef()
  }
}

function pathBucket(): string {
  if (typeof window === 'undefined') return '/'
  const path = (window.location.pathname || '/').split('?')[0]
  const cleaned = path.replace(/[^A-Za-z0-9/_-]/g, '').slice(0, 64)
  return cleaned.startsWith('/') ? cleaned || '/' : `/${cleaned}`
}

function sourceKindFrom(raw: string | undefined | null): string {
  const value = (raw || '').trim().toLowerCase()
  if (value === 'site_chatbot') return 'site_chatbot'
  if (value === 'consultation_intake' || value === 'consultation_intake_short') {
    return value === 'consultation_intake' ? 'consultation_intake' : 'consultation_intake_short'
  }
  if (!value) return 'organic'
  return 'other'
}

function fingerprint(eventName: string, dedupeKey: string): string {
  return `${eventName}:${dedupeKey}`
}

async function postEvents(events: QueuedEvent[]): Promise<void> {
  if (!events.length || typeof window === 'undefined') return
  try {
    await fetch(EVENTS_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        session_ref: getSiteAnalyticsSessionRef(),
        events,
      }),
      keepalive: true,
    })
  } catch {
    // Analytics must never break UX
  }
}

export function trackSiteMarketingEvent(
  eventName: SiteMarketingEventName,
  properties?: EventProps,
  dedupeKey?: string
): void {
  if (typeof window === 'undefined') return
  const key = fingerprint(eventName, dedupeKey || 'once')
  if (flushSeen.has(key)) return
  // Per-session once for coarse events; step views use step_id as dedupe.
  if (
    eventName === 'intake_started' ||
    eventName === 'intake_submitted' ||
    eventName === 'chatbot_opened' ||
    eventName === 'chatbot_first_message' ||
    eventName === 'intake_step_viewed' ||
    dedupeKey
  ) {
    flushSeen.add(key)
  }

  void postEvents([
    {
      event_name: eventName,
      properties: properties || {},
      dedupe_key: dedupeKey,
      client_timestamp: new Date().toISOString(),
    },
  ])
}

export function trackIntakeStarted(source?: string): void {
  trackSiteMarketingEvent('intake_started', { source_kind: sourceKindFrom(source) }, 'once')
}

export function trackIntakeStepViewed(stepId: string): void {
  trackSiteMarketingEvent('intake_step_viewed', { step_id: stepId }, stepId)
}

export function trackIntakeSubmitted(args: {
  source?: string
  preferredNextStep?: string
  priorityBand?: string
}): void {
  const props: EventProps = { source_kind: sourceKindFrom(args.source) }
  if (args.preferredNextStep) props.preferred_next_step = args.preferredNextStep
  if (args.priorityBand) props.priority_band = args.priorityBand
  trackSiteMarketingEvent('intake_submitted', props, 'once')
}

export function trackBookingClicked(surface = 'intake_success'): void {
  trackSiteMarketingEvent('booking_clicked', { surface }, `${surface}:${Date.now()}`)
}

export function trackChatbotOpened(): void {
  trackSiteMarketingEvent('chatbot_opened', { path_bucket: pathBucket() }, 'once')
}

export function trackChatbotFirstMessage(): void {
  trackSiteMarketingEvent('chatbot_first_message', {}, 'once')
}

export function trackChatbotFallback(mode?: string): void {
  trackSiteMarketingEvent(
    'chatbot_fallback',
    { mode: (mode || 'fallback').slice(0, 32) },
    `fallback:${Date.now()}`
  )
}

export function trackChatbotHandoff(handoffType?: string | null): void {
  const type =
    handoffType === 'contact' || handoffType === 'intake' ? handoffType : 'other'
  trackSiteMarketingEvent('chatbot_handoff', { handoff_type: type }, `handoff:${type}`)
}

/** Test helper */
export function _resetSiteMarketingAnalyticsForTests(): void {
  flushSeen.clear()
}
