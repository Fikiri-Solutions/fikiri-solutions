import { useState } from 'react'
import {
  Container,
  Button,
  Navbar,
  Footer,
  BentoCard,
  Testimonials,
  Heading,
  Subheading,
  AnimatedBackground,
} from '@/components/radiant'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'
import { publicMedia } from '@/lib/publicMedia'

function Hero() {
  return (
    <div className="relative">
      <Container className="relative">
        <Navbar />
        <div className="pt-12 pb-20 sm:pt-24 sm:pb-32 md:pt-32 md:pb-48 text-center px-2">
          <h1 className="font-display text-3xl font-medium tracking-tight text-balance text-foreground sm:text-4xl md:text-5xl lg:text-7xl xl:text-8xl mx-auto max-w-4xl">
            Automate your outreach. Close more deals.
          </h1>
          <p className="mt-6 sm:mt-8 max-w-lg text-base sm:text-xl font-medium text-muted-foreground md:text-2xl mx-auto px-1">
            Save money by automating. We connect your email, CRM, and calendar so you respond faster and never drop a lead.
          </p>
          <div className="mt-8 sm:mt-12 flex flex-col gap-3 sm:flex-row sm:gap-4 justify-center">
            <Button to="/signup" className="w-full sm:w-auto">Get started</Button>
            <Button variant="secondary" to="/pricing" className="w-full sm:w-auto">
              See pricing
            </Button>
          </div>
        </div>
      </Container>
    </div>
  )
}

/**
 * In-app screen snapshots: `public/images/preview-tab-*.png` (see `publicMedia.landing.tab`).
 * Renders in the **lower** product-preview block (under the Features bento), not in the bento images.
 */
const previewTabs = [
  { key: 'dashboard', label: 'Dashboard', image: publicMedia.landing.tab.dashboard },
  { key: 'inbox', label: 'Inbox', image: publicMedia.landing.tab.inbox },
  { key: 'crm', label: 'CRM', image: publicMedia.landing.tab.crm },
  { key: 'automations', label: 'Automations', image: publicMedia.landing.tab.automations },
] as const

function FeatureSection() {
  const [active, setActive] = useState(0)
  const current = previewTabs[active]

  return (
    <div className="overflow-hidden">
      <Container className="pb-24">
        <Heading as="h2" className="max-w-3xl">
          One place for email, CRM, and scheduling.
        </Heading>

        {/* Tab bar */}
        <div className="mt-8 sm:mt-12 flex max-w-3xl flex-wrap items-center justify-center gap-2 sm:mx-auto">
          {previewTabs.map((tab, i) => (
            <button
              key={tab.key}
              onClick={() => setActive(i)}
              type="button"
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors sm:px-4 ${
                i === active
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'bg-muted/60 text-muted-foreground hover:bg-muted'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* App preview — your PNGs 1:1 (object-contain); warm gradient ties into section below */}
        <div className="mt-6 sm:mt-8 flex justify-center px-1 sm:px-0">
          <div className="relative w-full max-w-4xl overflow-hidden rounded-2xl bg-background/50 shadow-sm ring-1 ring-border/30 dark:bg-muted/20 dark:ring-border/50">
            <div className="relative flex w-full min-h-[280px] max-h-[min(60vh,560px)] items-start justify-center sm:min-h-[320px]">
              <img
                key={current.key}
                src={current.image}
                alt={`${current.label} preview`}
                sizes="(max-width: 640px) 100vw, 56rem"
                className="h-auto w-full max-h-[min(60vh,560px)] object-contain object-top"
                loading="lazy"
                decoding="async"
              />
              <div
                className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-[#FDF2E9]/20 to-[#F4E0D2]/90 dark:from-transparent dark:via-white/[0.04] dark:to-background/80"
                aria-hidden
              />
            </div>
          </div>
        </div>
      </Container>
    </div>
  )
}

function BentoSection() {
  const featureImageClasses =
    'h-48 sm:h-52 md:h-56 lg:h-64'

  return (
    <Container>
      <Subheading>Features</Subheading>
      <Heading as="h3" className="mt-2 max-w-3xl">
        Built to save you money—automate more, do more with less.
      </Heading>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:mt-12 md:grid-cols-2 md:gap-6 lg:mt-16 lg:grid-cols-3">
        <BentoCard
          eyebrow="Email"
          title="AI-powered replies"
          description="Draft and send professional responses in seconds. Templates and AI suggestions keep your tone consistent and on-brand."
          graphicClassName={featureImageClasses}
          graphic={
            <div className="h-full w-full overflow-hidden rounded-t-2xl bg-muted/30">
              <img
                src={publicMedia.landing.bento.email}
                alt="Email feature preview"
                className="h-full w-full object-cover object-center transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                loading="lazy"
                decoding="async"
              />
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="CRM"
          title="Leads in one place"
          description="Track contacts, deals, and activity. Automatically create and update records from email and calendar."
          graphicClassName={featureImageClasses}
          graphic={
            <div className="h-full w-full overflow-hidden rounded-t-2xl bg-muted/30">
              <img
                src={publicMedia.landing.bento.crm}
                alt="CRM feature preview"
                className="h-full w-full object-cover object-[50%_38%] transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                loading="lazy"
                decoding="async"
              />
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="Automations"
          title="Workflows that run for you"
          description="Rules, triggers, and follow-ups that run on their own. Set it once and let Fikiri handle the rest—from lead capture to reminders."
          graphicClassName={featureImageClasses}
          graphic={
            <div className="h-full w-full overflow-hidden rounded-t-2xl bg-muted/30">
              <img
                src={publicMedia.landing.bento.automation}
                alt="Automations feature preview"
                className="h-full w-full object-cover object-center transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                loading="lazy"
                decoding="async"
              />
            </div>
          }
          fade={['bottom']}
        />
      </div>
    </Container>
  )
}

export default function RadiantLandingPage() {
  return (
    <div className="overflow-hidden bg-background text-foreground relative min-h-screen">
      {/* Light: animated gradient. Dark: solid dark bg (see .dark .fikiri-gradient-animated in index.css) so text is readable */}
      <div className="absolute inset-0 fikiri-gradient-animated">
        <AnimatedBackground />
      </div>
      <div className="relative z-10">
        <Hero />
        <main>
          <div className="py-24">
            <BentoSection />
            <div className="pt-4 sm:pt-8">
              <FeatureSection />
            </div>
          </div>
        </main>
        <Testimonials />
        <Footer />
      </div>
      <PublicChatbotWidget />
    </div>
  )
}
