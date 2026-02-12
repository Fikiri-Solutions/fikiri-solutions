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
} from '@/components/radiant'

function Hero() {
  return (
    <div className="relative">
      <Gradient className="absolute inset-2 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-20" />
      <Container className="relative">
        <Navbar />
        <div className="pt-16 pb-24 sm:pt-24 sm:pb-32 md:pt-32 md:pb-48 text-center">
          <h1 className="font-display text-5xl font-medium tracking-tight text-balance text-foreground sm:text-7xl md:text-8xl mx-auto">
            Automate your outreach. Close more deals.
          </h1>
          <p className="mt-8 max-w-lg text-xl font-medium text-muted-foreground sm:text-2xl mx-auto">
            Fikiri connects your email, CRM, and calendar so you respond faster and never drop a lead.
          </p>
          <div className="mt-12 flex flex-col gap-x-6 gap-y-4 sm:flex-row justify-center">
            <Button to="/signup">Get started</Button>
            <Button variant="secondary" to="/pricing">
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
        <div className="mt-16 flex justify-center">
          <div className="relative h-80 w-full max-w-4xl overflow-hidden rounded-2xl shadow-lg ring-1 ring-border">
            <Gradient className="absolute inset-0" />
            <div className="absolute inset-2 rounded-xl bg-white/90 dark:bg-gray-900/90" />
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
        Built for teams who care about response time.
      </Heading>
      <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-16 lg:grid-cols-3">
        <BentoCard
          eyebrow="Email"
          title="AI-powered replies"
          description="Draft and send professional responses in seconds. Templates and AI suggestions keep your tone consistent and on-brand."
          graphic={
            <div className="h-80 bg-muted flex items-center justify-center">
              <span className="text-4xl text-muted-foreground">✉️</span>
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="CRM"
          title="Leads in one place"
          description="Track contacts, deals, and activity. Automatically create and update records from email and calendar."
          graphic={
            <div className="h-80 bg-muted flex items-center justify-center">
              <span className="text-4xl text-muted-foreground">👥</span>
            </div>
          }
          fade={['bottom']}
        />
        <BentoCard
          eyebrow="Integrations"
          title="Connect your stack"
          description="Gmail, Outlook, Google Calendar, and more. One dashboard instead of tab-switching between tools."
          graphic={
            <div className="h-80 bg-muted flex items-center justify-center">
              <span className="text-4xl text-muted-foreground">🔗</span>
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
    <div className="overflow-hidden bg-background text-foreground">
      <Hero />
      <main>
        <div className="bg-gradient-to-b from-background from-50% to-muted py-24">
          <FeatureSection />
          <BentoSection />
        </div>
      </main>
      <Testimonials />
      <Footer />
    </div>
  )
}
