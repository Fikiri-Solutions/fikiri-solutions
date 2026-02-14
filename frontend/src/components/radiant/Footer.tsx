import { PlusGrid, PlusGridItem, PlusGridRow } from './PlusGrid'
import { Button } from './Button'
import { Container } from './Container'
import { Gradient } from './Gradient'
import { RadiantLink } from './RadiantLink'
import { FikiriLogo } from '@/components/FikiriLogo'
import { Subheading } from './Text'
import { AnimatedFikiriLogo } from './AnimatedFikiriLogo'
import { ExternalLink } from 'lucide-react'

const SOCIAL_LINKS = [
  { label: 'Twitter', href: 'https://twitter.com/fikirisolutions', aria: 'Fikiri on Twitter' },
  { label: 'Instagram', href: 'https://www.instagram.com/fikirisolutions', aria: 'Fikiri on Instagram' },
  { label: 'Facebook', href: 'https://www.facebook.com/fikirisolutions', aria: 'Fikiri on Facebook' },
  { label: 'LinkedIn', href: 'https://www.linkedin.com/company/fikirisolutions', aria: 'Fikiri on LinkedIn' },
] as const

function CallToAction() {
  return (
    <div className="relative pt-20 pb-16 text-center sm:py-24">
      <hgroup>
        <Subheading>Get started</Subheading>
        <p className="mt-6 text-3xl font-medium tracking-tight text-foreground sm:text-5xl">
          Ready to grow?
          <br />
          Start your 7-day free trial today.
        </p>
      </hgroup>
      <p className="mx-auto mt-6 max-w-sm text-sm text-muted-foreground">
        Connect your tools, automate workflows, save money, and let AI help you close more deals.
      </p>
      <div className="mt-6">
        <Button to="/signup" className="w-full sm:w-auto">
          Get started
        </Button>
      </div>
    </div>
  )
}

function SitemapHeading({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-medium text-muted-foreground">{children}</h3>
}

function SitemapLinks({ children }: { children: React.ReactNode }) {
  return <ul className="mt-6 space-y-4 text-sm">{children}</ul>
}

function SitemapLink(props: React.ComponentPropsWithoutRef<typeof RadiantLink>) {
  return (
    <li>
      <RadiantLink {...props} className="font-medium text-foreground hover:text-muted-foreground" />
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
          <SitemapLink to="/automations">Automations</SitemapLink>
        </SitemapLinks>
      </div>
      <div>
        <SitemapHeading>Company</SitemapHeading>
        <SitemapLinks>
          <SitemapLink to="/about">About</SitemapLink>
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
        <ul className="mt-6 flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {SOCIAL_LINKS.map(({ label, href, aria }) => (
            <li key={label}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={aria}
                className="font-medium text-foreground hover:text-muted-foreground inline-flex items-center gap-1.5"
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

function Copyright() {
  return (
    <div className="text-sm text-foreground">
      &copy; {new Date().getFullYear()} Fikiri Solutions
    </div>
  )
}

export function Footer() {
  return (
    <footer>
      <Gradient className="relative">
        <div className="absolute inset-2 rounded-3xl bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm" />
        <Container>
          <CallToAction />
          <PlusGrid className="pb-16">
            <PlusGridRow>
              <div className="grid grid-cols-2 gap-y-10 pb-6 lg:grid-cols-6 lg:gap-8">
                <div className="col-span-2 flex items-center">
                  <PlusGridItem className="pt-6 lg:pb-6">
                    <AnimatedFikiriLogo />
                  </PlusGridItem>
                </div>
                <div className="col-span-2 grid grid-cols-2 gap-x-8 gap-y-12 lg:col-span-4 lg:grid-cols-subgrid lg:pt-6">
                  <Sitemap />
                </div>
              </div>
            </PlusGridRow>
            <PlusGridRow>
              <div>
                <PlusGridItem className="py-3">
                  <Copyright />
                </PlusGridItem>
              </div>
            </PlusGridRow>
          </PlusGrid>
        </Container>
      </Gradient>
    </footer>
  )
}
