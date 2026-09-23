/** Canonical production origin — keep aligned with index.html / vercel redirects. */
export const SITE_ORIGIN = 'https://fikirisolutions.com'

export const DEFAULT_OG_IMAGE = `${SITE_ORIGIN}/og-image.png`

export type PublicPageSeo = {
  /** Pathname beginning with `/` (use `/` for home). */
  path: string
  title: string
  description: string
  /** Include in /sitemap.xml when true (default true). */
  sitemap?: boolean
  changefreq?: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never'
  priority?: number
  /** Optional robots override (e.g. noindex for utility pages). */
  robots?: string
}

/**
 * Indexable / shareable public marketing routes.
 * Keep in sync with App.tsx public routes and public/sitemap.xml (see tests).
 */
export const PUBLIC_PAGE_SEO: readonly PublicPageSeo[] = [
  {
    path: '/',
    title: 'Fikiri Solutions - AI-Powered Business Automation Platform',
    description:
      'Transform your business with AI-powered email automation, CRM management, and lead analysis. Specialized solutions for landscaping, restaurants, and medical practices.',
    changefreq: 'daily',
    priority: 1.0,
  },
  {
    path: '/about',
    title: 'About Fikiri Solutions | Consulting-First Workflow Systems',
    description:
      'Learn how Fikiri maps real business workflows, then builds practical email, CRM, and automation systems around how your team already works.',
    changefreq: 'monthly',
    priority: 0.8,
  },
  {
    path: '/contact',
    title: 'Contact Fikiri Solutions',
    description:
      'Questions, feedback, or a demo? Contact Fikiri Solutions — or complete a consultation intake so we can focus on your workflow.',
    changefreq: 'monthly',
    priority: 0.8,
  },
  {
    path: '/intake',
    title: 'Consultation Intake | Fikiri Solutions',
    description:
      'Start a workflow conversation with Fikiri. Share how your business operates so we can prepare a practical consultation.',
    changefreq: 'monthly',
    priority: 0.9,
  },
  {
    path: '/pricing',
    title: 'Pricing | Fikiri Solutions',
    description:
      'Fikiri Solutions pricing for AI email automation, CRM, and workflow systems. Compare plans and start a trial.',
    changefreq: 'weekly',
    priority: 0.9,
  },
  {
    path: '/faq',
    title: 'FAQ | Fikiri Solutions',
    description:
      'Answers about Fikiri Solutions automation platform, onboarding, Gmail/Outlook integrations, pricing, and support.',
    changefreq: 'monthly',
    priority: 0.7,
  },
  {
    path: '/privacy',
    title: 'Privacy Policy - Fikiri Solutions',
    description:
      'Privacy Policy for Fikiri Solutions AI-powered business automation platform, including data use, cookies, and your rights.',
    changefreq: 'monthly',
    priority: 0.4,
  },
  {
    path: '/terms',
    title: 'Terms of Service - Fikiri Solutions',
    description:
      'Terms of Service for using the Fikiri Solutions AI-powered business automation platform.',
    changefreq: 'monthly',
    priority: 0.4,
  },
  {
    path: '/sms-opt-in',
    title: 'SMS Opt-In - Fikiri Solutions',
    description:
      'Consent to receive SMS text messages from Fikiri Solutions LLC. Opt-in language and proof of consent.',
    changefreq: 'yearly',
    priority: 0.3,
  },
  {
    path: '/services-landing',
    title: 'Services | Fikiri Solutions',
    description:
      'Explore Fikiri services for email automation, CRM management, and intelligent workflows built around your operations.',
    changefreq: 'weekly',
    priority: 0.7,
  },
  {
    path: '/ai-landing',
    title: 'AI Assistant | Fikiri Solutions',
    description:
      'See how Fikiri’s AI assistant helps teams draft replies, prioritize work, and automate routine business communication.',
    changefreq: 'weekly',
    priority: 0.7,
  },
  {
    path: '/industries/landscaping',
    title: 'Landscaping Automation | Fikiri Solutions',
    description:
      'Workflow automation for landscaping businesses — inbound requests, follow-ups, and CRM systems tailored to field service ops.',
    changefreq: 'weekly',
    priority: 0.8,
  },
  {
    path: '/industries/restaurant',
    title: 'Restaurant Automation | Fikiri Solutions',
    description:
      'Automation for restaurants and hospitality — guest inquiries, reservations follow-up, and CRM workflows that reduce inbox chaos.',
    changefreq: 'weekly',
    priority: 0.8,
  },
  {
    path: '/industries/medical',
    title: 'Medical Practice Automation | Fikiri Solutions',
    description:
      'Practical automation for medical and dental practices — patient inquiries, scheduling follow-ups, and organized CRM workflows.',
    changefreq: 'weekly',
    priority: 0.8,
  },
  {
    path: '/install',
    title: 'Install Fikiri Chat | Fikiri Solutions',
    description:
      'Install and embed the Fikiri site assistant on WordPress, Wix, Squarespace, Shopify, and custom sites.',
    changefreq: 'monthly',
    priority: 0.5,
  },
  {
    path: '/landing-classic',
    title: 'Fikiri Solutions | Classic Landing',
    description:
      'Fikiri Solutions AI-powered business automation for email, CRM, and lead management.',
    sitemap: false,
    robots: 'noindex, follow',
  },
] as const

const byPath = new Map(PUBLIC_PAGE_SEO.map((entry) => [entry.path, entry]))

export function getPublicPageSeo(path: string): PublicPageSeo | undefined {
  const normalized = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/'
  return byPath.get(normalized === '' ? '/' : normalized)
}

export function absoluteUrl(path: string): string {
  if (path === '/') return `${SITE_ORIGIN}/`
  return `${SITE_ORIGIN}${path.startsWith('/') ? path : `/${path}`}`
}

/** Entries that belong in sitemap.xml */
export function getSitemapEntries(): PublicPageSeo[] {
  return PUBLIC_PAGE_SEO.filter((e) => e.sitemap !== false)
}
