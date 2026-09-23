/**
 * Paths the Vite SPA legitimately handles (must stay in sync with App.tsx routes).
 * Used by Vercel Edge middleware to return HTTP 404 for unknown URLs while still
 * serving index.html so React Router can render the branded NotFound page.
 *
 * Lives under frontend/src/lib (not frontend/lib/) because root .gitignore ignores lib/.
 */

const EXACT = new Set([
  '/',
  '/landing-classic',
  '/pricing',
  '/faq',
  '/services-landing',
  '/ai-landing',
  '/industries/landscaping',
  '/industries/restaurant',
  '/industries/medical',
  '/about',
  '/contact',
  '/intake',
  '/install',
  '/sms-opt-in',
  '/terms',
  '/privacy',
  '/error',
  '/onboarding-flow',
  '/onboarding-flow/sync',
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
  '/onboarding',
  '/home',
  '/dashboard',
  '/services',
  '/crm',
  '/ai',
  '/assistant',
  '/industry',
  '/analytics',
  '/automations',
  '/automations/setup/capture-leads-email',
  '/debug/correlation',
  '/ai/chatbot-builder',
  '/import-center',
  '/integrations',
  '/integrations/gmail',
  '/integrations/outlook',
  '/billing',
  '/support/contact',
  '/inbox',
  '/gmail-status',
  '/privacy-settings',
  '/admin',
  '/admin/tenants',
  '/admin/audit',
  '/admin/security',
  '/admin/site-chat',
])

/** Prefix patterns for nested / param routes */
const PREFIXES = [
  '/onboarding-flow/',
  '/onboarding/',
  '/inbox/',
  '/admin/tenants/',
] as const

/** Strip query/hash; collapse trailing slash except root */
export function normalizePathname(pathname: string): string {
  const raw = (pathname || '/').split('?')[0].split('#')[0] || '/'
  if (raw.length > 1 && raw.endsWith('/')) return raw.slice(0, -1)
  return raw || '/'
}

export function isKnownSpaPath(pathname: string): boolean {
  const path = normalizePathname(pathname)
  if (EXACT.has(path)) return true
  return PREFIXES.some((prefix) => path.startsWith(prefix))
}

/** Static / build artifacts that must never be treated as SPA 404 candidates */
export function isStaticAssetPath(pathname: string): boolean {
  const path = normalizePathname(pathname)
  if (path === '/index.html') return true
  // Any path with a file extension (favicon.ico, *.js, *.webp, robots.txt, …)
  if (/\.[a-zA-Z0-9]{1,8}$/.test(path)) return true
  const staticPrefixes = [
    '/assets/',
    '/fonts/',
    '/icons/',
    '/img/',
    '/images/',
    '/optimized/',
    '/media/',
    '/brand/',
  ]
  return staticPrefixes.some((p) => path.startsWith(p))
}
