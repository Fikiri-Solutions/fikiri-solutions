/**
 * Demo-safe gating for client demos and consulting-first positioning.
 * Enable with VITE_DEMO_SAFE_MODE=true on the frontend build (e.g. Vercel).
 *
 * Does not change backend behavior — navigation, labels, and UI gates only.
 */

function envTruthy(raw: string | undefined): boolean {
  const v = (raw || '').trim().toLowerCase()
  return v === '1' || v === 'true' || v === 'yes' || v === 'on'
}

/** Master switch: hide unstable nav routes and gate unfinished product surfaces. */
export function isDemoSafeMode(): boolean {
  return envTruthy(import.meta.env.VITE_DEMO_SAFE_MODE)
}

/** Email Analyze / Suggest reply — only after OpenAI health check + in-app rehearsal. */
export function isEmailAiDemoEnabled(): boolean {
  return envTruthy(import.meta.env.VITE_DEMO_EMAIL_AI_ENABLED)
}

const DEMO_HIDDEN_NAV_HREFS = new Set([
  '/ai',
  '/assistant',
  '/ai/chatbot-builder',
  '/services',
  '/analytics',
  '/industry',
])

export function isNavHiddenInDemoSafeMode(href: string): boolean {
  if (!isDemoSafeMode()) return false
  if (DEMO_HIDDEN_NAV_HREFS.has(href)) return true
  if (href.startsWith('/ai/')) return true
  return false
}

export type DemoGatedRoute =
  | 'aiAssistant'
  | 'chatbotBuilder'
  | 'servicesPreview'
  | 'usageAnalytics'

const ROUTE_GATE: Record<DemoGatedRoute, () => boolean> = {
  aiAssistant: () => isDemoSafeMode(),
  chatbotBuilder: () => isDemoSafeMode(),
  servicesPreview: () => isDemoSafeMode(),
  usageAnalytics: () => isDemoSafeMode(),
}

export function isRouteGatedForDemo(route: DemoGatedRoute): boolean {
  return ROUTE_GATE[route]()
}

export const DEMO_UNAVAILABLE_COPY: Record<
  DemoGatedRoute,
  { title: string; body: string }
> = {
  aiAssistant: {
    title: 'AI Assistant not in this demo',
    body:
      'Live OpenAI-powered chat is verified separately before we show it to clients. ' +
      'For today: use CRM and Inbox (when email AI is enabled), or our marketing site assistant.',
  },
  chatbotBuilder: {
    title: 'Chatbot Builder not in this demo',
    body:
      'Tenant knowledge-base configuration is available after onboarding. ' +
      'Today we show the public site assistant and CRM workflow.',
  },
  servicesPreview: {
    title: 'Service settings preview',
    body:
      'This screen is a product preview — toggles are not persisted to your account yet. ' +
      'Fikiri engagements start with workflow discovery and custom configuration.',
  },
  usageAnalytics: {
    title: 'Usage analytics not in this demo',
    body: 'Advanced analytics is still rolling out. CRM and verified workflows are the focus today.',
  },
}
