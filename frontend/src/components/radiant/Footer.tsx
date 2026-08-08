import { Button } from './Button'
import { Container } from './Container'
import { RadiantLink } from './RadiantLink'
import { MarketingReveal } from './Reveal'
import { FikiriLogo } from '@/components/FikiriLogo'
import { ExternalLink } from 'lucide-react'

const SOCIAL_LINKS = [
  { label: 'X', href: 'https://x.com/FikiriSolutions', aria: 'Fikiri on X' },
  { label: 'Instagram', href: 'https://www.instagram.com/fikirisolutions/?hl=en', aria: 'Fikiri on Instagram' },
] as const

function CallToAction() {
  return (
    <MarketingReveal direction="scale">
      <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-black/35 px-6 py-12 text-center shadow-[0_0_60px_rgba(255,107,53,0.12)] backdrop-blur-sm sm:px-10 sm:py-14 sm:backdrop-blur-md">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(255,107,53,0.22),_transparent_58%)]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -right-16 bottom-0 h-48 w-48 rounded-full bg-orange-500/20 blur-3xl"
          aria-hidden
        />
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-orange-300">
            Next Step
          </p>
          <h2 className="mt-3 font-serif text-3xl font-medium tracking-tight text-white sm:text-4xl lg:text-5xl">
            Ready to map your workflow?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-white/75 sm:text-base">
            Start with a practical conversation about where automation, CRM, or AI can help your business.
          </p>
          <div className="mt-7 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
            <Button to="/intake" className="w-full sm:w-auto">
              Start a workflow conversation
            </Button>
            <Button
              to="/pricing"
              variant="secondary"
              className="w-full border-white/20 bg-white/10 text-white ring-white/20 hover:bg-white/15 sm:w-auto"
            >
              See pricing
            </Button>
          </div>
        </div>
      </div>
    </MarketingReveal>
  )
}

function SitemapHeading({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-medium text-white/80">{children}</h3>
}

function SitemapLinks({ children }: { children: React.ReactNode }) {
  return <ul className="mt-4 space-y-3 text-sm">{children}</ul>
}

function SitemapLink(props: React.ComponentPropsWithoutRef<typeof RadiantLink>) {
  return (
    <li>
      <RadiantLink
        {...props}
        className="inline-flex min-h-[44px] items-center font-medium text-white/65 transition-colors hover:text-white touch-manipulation"
      />
    </li>
  )
}

function Sitemap() {
  return (
    <>
      <div>
        <SitemapHeading>Product</SitemapHeading>
        <SitemapLinks>
          <SitemapLink to="/pricing">Pricing</SitemapLink>
          <SitemapLink to="/faq">FAQ</SitemapLink>
        </SitemapLinks>
      </div>
      <div>
        <SitemapHeading>Company</SitemapHeading>
        <SitemapLinks>
          <SitemapLink to="/about">About</SitemapLink>
          <SitemapLink to="/contact">Contact us</SitemapLink>
        </SitemapLinks>
      </div>
      <div>
        <SitemapHeading>Legal</SitemapHeading>
        <SitemapLinks>
          <SitemapLink to="/terms">Terms of service</SitemapLink>
          <SitemapLink to="/privacy">Privacy policy</SitemapLink>
        </SitemapLinks>
      </div>
      <div>
        <SitemapHeading>Follow us</SitemapHeading>
        <ul className="mt-4 flex flex-col gap-y-2 text-sm">
          {SOCIAL_LINKS.map(({ label, href, aria }) => (
            <li key={label}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={aria}
                className="inline-flex min-h-[44px] items-center gap-1.5 font-medium text-white/65 transition-colors hover:text-white touch-manipulation"
              >
                <ExternalLink className="h-4 w-4 shrink-0" aria-hidden />
                {label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}

export function Footer({ showCta = true }: { showCta?: boolean }) {
  return (
    <footer className="relative border-t border-white/10 bg-black/20">
      <Container className="relative py-12 sm:py-16">
        {showCta && (
          <div className="mb-12 sm:mb-14">
            <CallToAction />
          </div>
        )}

        <div className="grid grid-cols-2 gap-y-10 gap-x-8 lg:grid-cols-6">
          <div className="col-span-2 flex items-start">
            <RadiantLink to="/" title="Home" className="inline-flex">
              <FikiriLogo size="md" variant="white" className="h-10 w-auto sm:h-12" />
            </RadiantLink>
          </div>
          <div className="col-span-2 grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-4 lg:col-span-4 lg:pt-1">
            <Sitemap />
          </div>
        </div>

        <div className="mt-10 border-t border-white/10 pt-5 text-sm text-white/55">
          &copy; {new Date().getFullYear()} Fikiri Solutions
        </div>
      </Container>
    </footer>
  )
}
