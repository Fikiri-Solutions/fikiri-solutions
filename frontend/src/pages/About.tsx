import React from 'react'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'
import { publicMedia } from '../lib/publicMedia'

const serviceCards: {
  imageSrc: string
  title: string
  description: string
}[] = [
  {
    imageSrc: publicMedia.about.serviceEmail,
    title: 'Email Automation',
    description: 'AI-powered email processing and response automation',
  },
  {
    imageSrc: publicMedia.about.serviceCrm,
    title: 'CRM Management',
    description: 'Customer relationship management and lead tracking',
  },
  {
    imageSrc: publicMedia.about.serviceAi,
    title: 'AI Assistant',
    description: 'Intelligent business automation and analytics',
  },
]

export const About: React.FC = () => {
  return (
    <RadiantLayout>
      <div className="min-h-screen bg-background text-foreground relative">
        <div className="absolute inset-0 fikiri-gradient-animated">
          <AnimatedBackground />
        </div>
        {/* Hero */}
        <section className="relative py-16 sm:py-20 z-10">
          <Gradient className="absolute inset-x-2 top-0 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-20" />
          <Container className="relative">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-4xl font-bold text-foreground mb-4 sm:text-5xl">
                About Fikiri Solutions
              </h1>
              <p className="text-xl text-muted-foreground">
                We help small and large businesses save money through automation.
              </p>
            </div>
          </Container>
        </section>

        {/* Main Content */}
        <section className="py-16 relative z-10">
          <Container>
            {/* Services */}
            <h2 className="text-2xl font-semibold text-foreground mb-6">
              Our Services
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
              {serviceCards.map((card) => (
                <article
                  key={card.imageSrc}
                  className="group text-center relative overflow-hidden flex flex-col rounded-2xl bg-card/40 backdrop-blur-sm shadow-md shadow-stone-900/8 ring-1 ring-stone-900/6 dark:ring-white/8"
                >
                  <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/5 via-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  <div className="relative w-full aspect-[3/4] min-h-[220px] sm:min-h-[280px]">
                    <img
                      src={card.imageSrc}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover object-center"
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <div className="relative border-t border-stone-900/5 bg-gradient-to-b from-card/30 to-card/50 px-5 pb-6 pt-4 dark:border-white/5 dark:from-white/[0.04] dark:to-white/[0.07] sm:px-6">
                    <h3 className="text-lg font-medium text-foreground mb-1.5">
                      {card.title}
                    </h3>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {card.description}
                    </p>
                  </div>
                </article>
              ))}
            </div>

            {/* Specializations / social proof by example */}
            <h2 className="text-2xl font-semibold text-foreground mb-2">
              Industry Examples
            </h2>
            <p className="text-sm text-muted-foreground mb-6 max-w-2xl">
              We partner with service-driven businesses of all sizes. Here are a few places where teams are already using Fikiri to save time every week:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm relative overflow-hidden">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-green-500/5 via-emerald-500/5 to-transparent opacity-60" />
                <div className="relative">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Landscaping
                </h3>
                <p className="text-muted-foreground text-sm">
                  Owner-operators use Fikiri to keep clients updated, follow up on quotes, and stay ahead of seasonal work.
                </p>
                </div>
              </div>
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm relative overflow-hidden">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/5 via-red-500/5 to-transparent opacity-60" />
                <div className="relative">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Restaurants
                </h3>
                <p className="text-muted-foreground text-sm">
                  Multi-location teams streamline guest messaging, reservations, and feedback without adding staff.
                </p>
                </div>
              </div>
              <div className="text-center p-6 bg-card/90 backdrop-blur-sm border border-border rounded-2xl shadow-sm relative overflow-hidden">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/5 via-indigo-500/5 to-transparent opacity-60" />
                <div className="relative">
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Medical Practices
                </h3>
                <p className="text-muted-foreground text-sm">
                  Clinics use Fikiri to reduce no-shows and keep patients informed before and after visits.
                </p>
                </div>
              </div>
            </div>

            <p className="mt-4 text-sm text-muted-foreground">
              Not in one of these industries? If you talk to customers, book work, or manage follow-ups, Fikiri can likely help your business too.
            </p>

            {/* Business Information – moved to bottom with subtle gradient */}
            <div className="mt-16 bg-card/95 backdrop-blur-sm rounded-2xl border border-border/80 shadow-sm p-8 relative overflow-hidden">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-orange-500/10 via-red-500/10 to-transparent opacity-80" />
              <div className="relative grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h2 className="text-2xl font-semibold text-foreground mb-4">
                    Business Information
                  </h2>
                  <h3 className="text-lg font-medium text-foreground mb-4">
                    Company Details
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-muted-foreground">Business Name:</span>
                      <p className="text-foreground">Fikiri Solutions</p>
                    </div>
                    <div>
                      <span className="font-medium text-muted-foreground">Industry:</span>
                      <p className="text-foreground">AI-Powered Business Automation</p>
                    </div>
                    <div>
                      <span className="font-medium text-muted-foreground">Website:</span>
                      <p className="text-foreground">https://fikirisolutions.com</p>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-foreground mb-4">
                    Contact Information
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-muted-foreground">Location:</span>
                      <p className="text-foreground">
                        Florida, United States
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Container>
        </section>
      </div>
      <PublicChatbotWidget />
    </RadiantLayout>
  )
}
