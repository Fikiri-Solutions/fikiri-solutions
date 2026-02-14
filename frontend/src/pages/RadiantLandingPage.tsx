import {
  Container,
  Button,
  Gradient,
  Navbar,
  Footer,
  BentoCard,
  Testimonials,
  Heading,
  Subheading,
  AnimatedBackground,
} from '@/components/radiant'
import { EmailIcon } from '@/components/icons/EmailIcon'
import { CRMIcon } from '@/components/icons/CRMIcon'
import { IntegrationsIcon } from '@/components/icons/IntegrationsIcon'

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

function FeatureSection() {
  return (
    <div className="overflow-hidden">
      <Container className="pb-24">
        <Heading as="h2" className="max-w-3xl">
          One place for email, CRM, and scheduling.
        </Heading>
        <div className="mt-10 sm:mt-16 flex justify-center">
          <div className="relative h-48 sm:h-64 md:h-80 w-full max-w-4xl overflow-hidden rounded-2xl shadow-lg ring-1 ring-border">
            <Gradient className="absolute inset-0" />
            <div className="absolute inset-2 rounded-xl bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-medium text-muted-foreground">
                Dashboard preview
              </span>
            </div>
          </div>
        </div>
      </Container>
    </div>
  )
}

function BentoSection() {
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
          graphic={
            <div className="h-80 bg-white/50 dark:bg-gray-800/50 flex items-center justify-center p-8">
              <EmailIcon className="w-48 h-32" />
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="CRM"
          title="Leads in one place"
          description="Track contacts, deals, and activity. Automatically create and update records from email and calendar."
          graphic={
            <div className="h-80 bg-white/50 dark:bg-gray-800/50 flex items-center justify-center p-8">
              <CRMIcon className="w-48 h-36" />
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="Automations"
          title="Workflows that run for you"
          description="Rules, triggers, and follow-ups that run on their own. Set it once and let Fikiri handle the rest—from lead capture to reminders."
          graphic={
            <div className="h-80 bg-white/50 dark:bg-gray-800/50 flex items-center justify-center p-8">
              <IntegrationsIcon className="w-48 h-48" />
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
            <FeatureSection />
            <BentoSection />
          </div>
        </main>
        <Testimonials />
        <Footer />
      </div>
    </div>
  )
}
