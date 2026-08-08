import { useId, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  Container,
  Button,
  Navbar,
  Footer,
  BentoCard,
  ClientPartnerships,
  Heading,
  Subheading,
  MarketingBackdrop,
  Reveal,
} from '@/components/radiant'
import { MarketingChatWidget } from '../components/MarketingChatWidget'
import { SectorFitSection } from '../components/SectorFitExplorer'
import { publicMedia } from '@/lib/publicMedia'
import { trackSectorExplorerCta } from '../lib/sectorFitAnalytics'

function Hero() {
  const sectorHeadingId = useId()
  const reduceMotion = useReducedMotion()

  return (
    <div className="relative isolate">
      <Container className="relative">
        <Navbar tone="onDark" variant="marketing" />
        <motion.div
          className="px-2 pb-12 pt-4 sm:pb-16 sm:pt-6 md:pb-20"
          initial={reduceMotion ? false : { opacity: 0, y: 28, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
        >
          <SectorFitSection headingId={sectorHeadingId} tone="onDark" />
          <motion.div
            className="mt-6 flex flex-col items-stretch justify-center gap-3 sm:mt-8 sm:flex-row sm:items-center sm:gap-4"
            initial={reduceMotion ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
          >
            <Button
              to="/signup"
              className="w-full sm:w-auto"
              onClick={() => trackSectorExplorerCta('signup')}
            >
              Get started
            </Button>
            <Button
              variant="secondary"
              to="/intake"
              className="w-full border-white/20 bg-white/10 text-white ring-white/20 hover:bg-white/15 sm:w-auto"
              onClick={() => trackSectorExplorerCta('intake')}
            >
              Start a workflow conversation
            </Button>
          </motion.div>
          <p className="mt-4 text-center text-sm text-white/75">
            Prefer pricing first?{' '}
            <a
              href="/pricing"
              className="font-medium text-orange-300 underline-offset-2 hover:text-orange-200 hover:underline"
              onClick={() => trackSectorExplorerCta('pricing')}
            >
              See plans
            </a>
          </p>
        </motion.div>
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

function PreviewTabImage({ src, alt }: { src: string; alt: string }) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.img
      src={src}
      alt={alt}
      sizes="(max-width: 640px) 100vw, 56rem"
      className="h-auto w-full max-h-[min(52vh,480px)] object-contain object-top"
      loading="lazy"
      decoding="async"
      initial={reduceMotion ? false : { opacity: 0.35, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
    />
  )
}

function FeatureSection() {
  const [active, setActive] = useState(0)
  const current = previewTabs[active]

  return (
    <div className="overflow-hidden">
      <Container>
        <Reveal direction="up">
          <Heading as="h2" dark className="max-w-3xl">
            One place for email, CRM, and scheduling.
          </Heading>
        </Reveal>

        <Reveal direction="up" delay={0.1}>
          <div className="mt-6 flex max-w-3xl flex-wrap items-center justify-center gap-2 sm:mx-auto sm:mt-8">
            {previewTabs.map((tab, i) => (
              <button
                key={tab.key}
                onClick={() => setActive(i)}
                type="button"
                className={`min-h-[44px] touch-manipulation rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 sm:px-4 ${
                  i === active
                    ? 'scale-[1.02] bg-primary text-primary-foreground shadow-md shadow-brand-primary/25'
                    : 'bg-white/15 text-white/85 ring-1 ring-white/25 hover:bg-white/20 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </Reveal>

        <Reveal direction="scale" delay={0.16} className="mt-5 sm:mt-6">
          <div className="flex justify-center px-1 sm:px-0">
            <div className="relative w-full max-w-4xl overflow-hidden rounded-2xl bg-white/90 shadow-lg shadow-orange-950/30 ring-1 ring-white/20 transition-shadow duration-300 hover:shadow-xl hover:shadow-brand-primary/20">
              <div className="relative flex w-full min-h-[240px] max-h-[min(52vh,480px)] items-start justify-center sm:min-h-[280px]">
                <PreviewTabImage key={current.key} src={current.image} alt={`${current.label} preview`} />
                <div
                  className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#140f0c]/35"
                  aria-hidden
                />
              </div>
            </div>
          </div>
        </Reveal>
      </Container>
    </div>
  )
}

function BentoSection() {
  const featureImageClasses = 'h-48 sm:h-52 md:h-56 lg:h-64'

  return (
    <Container>
      <Reveal direction="up">
        <Subheading dark>Workflow systems</Subheading>
        <Heading as="h3" dark className="mt-2 max-w-3xl">
          Practical automation built around how your business already works.
        </Heading>
        <p className="mt-4 max-w-2xl text-white/80">
          From discovery to implementation — email, CRM, and automations configured for real operations, not
          generic demos.
        </p>
      </Reveal>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:mt-10 md:grid-cols-2 md:gap-5 lg:grid-cols-3">
        <Reveal direction="up" delay={0.08}>
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
                  className="h-full w-full object-cover object-center transition-transform duration-500 ease-out motion-safe:group-hover:scale-[1.04]"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            }
            fade={['bottom']}
          />
        </Reveal>
        <Reveal direction="up" delay={0.16}>
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
                  className="h-full w-full object-cover object-[50%_38%] transition-transform duration-500 ease-out motion-safe:group-hover:scale-[1.04]"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            }
            fade={['bottom']}
          />
        </Reveal>
        <Reveal direction="up" delay={0.24}>
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
                  className="h-full w-full object-cover object-center transition-transform duration-500 ease-out motion-safe:group-hover:scale-[1.04]"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            }
            fade={['bottom']}
          />
        </Reveal>
      </div>
    </Container>
  )
}

export default function RadiantLandingPage() {
  return (
    <div className="mobile-layout-root relative min-h-dvh overflow-x-hidden font-serif text-foreground">
      <MarketingBackdrop />
      <div className="relative z-10">
        <Hero />
        <main className="relative pb-[env(safe-area-inset-bottom)]">
          <div className="relative py-14 sm:py-16 lg:py-20">
            <div
              className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand-primary/40 to-transparent"
              aria-hidden
            />
            <BentoSection />
            <div className="pt-10 sm:pt-12">
              <FeatureSection />
            </div>
          </div>
        </main>
        <ClientPartnerships />
        <Footer />
      </div>
      <MarketingChatWidget />
    </div>
  )
}
