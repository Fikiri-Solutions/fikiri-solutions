import { Navbar } from './Navbar'
import { Footer } from './Footer'
import { MarketingBackdrop } from './MarketingBackdrop'
import { clsx } from 'clsx'

/**
 * Wraps public/marketing pages with Radiant-style Navbar + Footer.
 * Marketing variant: full-page dark charcoal/amber wash behind nav + content
 * (same treatment as the home hero). App variant reserved for solid chrome.
 */
export function RadiantLayout({
  children,
  variant = 'marketing',
  showFooterCta = true,
  backdropIntensity = 'strong',
}: {
  children: React.ReactNode
  variant?: 'marketing' | 'app'
  /** Marketing CTA band above sitemap. Hide on auth forms for focus. */
  showFooterCta?: boolean
  /** Soften motion behind auth/forms on small screens / focus tasks. */
  backdropIntensity?: 'subtle' | 'strong'
}) {
  const isMarketing = variant === 'marketing'

  return (
    <div
      className={clsx(
        'mobile-layout-root relative flex min-h-dvh flex-col font-serif text-foreground',
        !isMarketing && 'bg-background'
      )}
    >
      {isMarketing && <MarketingBackdrop intensity={backdropIntensity} />}
      <div className="relative z-10 flex min-h-dvh flex-col">
        <Navbar variant={isMarketing ? 'marketing' : 'app'} tone={isMarketing ? 'onDark' : 'default'} />
        <main className="relative z-10 flex-1 min-w-0 overflow-x-clip pb-[env(safe-area-inset-bottom)]">{children}</main>
        <Footer showCta={isMarketing ? showFooterCta : false} />
      </div>
    </div>
  )
}
