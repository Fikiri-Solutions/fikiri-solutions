/**
 * About page: one implementation for all viewports (not split mobile/desktop code paths).
 * Tailwind is mobile-first—unprefixed utilities apply to the smallest screens; sm/md/lg add or
 * adjust for larger breakpoints so desktop/content changes stay in sync while mobile stays usable.
 */
import React, { useCallback, useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { RadiantLayout, Container, Reveal } from '../components/radiant'
import { MarketingChatWidget } from '../components/MarketingChatWidget'
import { publicMedia } from '../lib/publicMedia'
import { cn } from '../lib/utils'

type ServiceCard = {
  id: string
  imageSrc: string
  imageAlt: string
  title: string
  teaser: string
  details: {
    bullets: string[]
    closing: string
  }
}

const serviceCards: ServiceCard[] = [
  {
    id: 'email-automation',
    imageSrc: publicMedia.about.serviceEmail,
    imageAlt: 'Abstract illustration suggesting automated email workflows',
    title: 'Email Automation',
    teaser:
      'Turn inbound mail into sorted threads, clear priorities, and faster replies—without hiring another inbox role.',
    details: {
      bullets: [
        'Classify and route messages so urgent client work surfaces first.',
        'Draft and structure responses your team can send in one click.',
        'Reduce repeat questions with consistent follow-up and templates.',
        'Works alongside Gmail and Outlook-style workflows your staff already use.',
      ],
      closing:
        'Goal: fewer missed leads, less manual triage, and more time on revenue work—not inbox housekeeping.',
    },
  },
  {
    id: 'crm-management',
    imageSrc: publicMedia.about.serviceCrm,
    imageAlt: 'Abstract illustration suggesting customer records and pipeline visibility',
    title: 'CRM Management',
    teaser:
      'One place for contacts, conversations, and next steps—so nothing falls through when the week gets busy.',
    details: {
      bullets: [
        'Keep leads and customers tied to real activity, not scattered spreadsheets.',
        'See stages and ownership so everyone knows who follows up and when.',
        'Merge duplicates and keep email as the stable identity across tools.',
        'Lightweight enough for small teams; structured enough as you grow.',
      ],
      closing:
        'We are not selling “enterprise CRM consulting”—we give operators a practical system that matches how they actually sell and serve.',
    },
  },
  {
    id: 'ai-assistant',
    imageSrc: publicMedia.about.serviceAi,
    imageAlt: 'Abstract illustration suggesting an AI copilot for business tasks',
    title: 'AI Assistant',
    teaser:
      'Context-aware help for your workflows—summaries, next actions, and answers grounded in how Fikiri runs.',
    details: {
      bullets: [
        'Ask about leads, follow-ups, and process questions without generic filler.',
        'Get concise summaries and suggestions aligned with your automation setup.',
        'Stay inside sensible limits: helpful output, not endless generic essays.',
        'Complements email + CRM automation instead of replacing your judgment.',
      ],
      closing:
        'Think copilot for daily operations: faster clarity, not a chatbot that guesses your business.',
    },
  },
]

export const About: React.FC = () => {
  const [openServiceId, setOpenServiceId] = useState<string | null>(null)
  const sectionHeadingId = useId()

  const toggleService = useCallback((id: string) => {
    setOpenServiceId((prev) => (prev === id ? null : id))
  }, [])

  return (
    <RadiantLayout>
      <div className="relative min-h-dvh overflow-x-hidden pb-[env(safe-area-inset-bottom)]">
        {/* Hero */}
        <section className="relative z-10 py-8 sm:py-12">
          <Container className="relative">
            <Reveal direction="up">
              <div className="max-w-3xl mx-auto text-center rounded-2xl bg-black/30 px-4 py-6 backdrop-blur-md ring-1 ring-white/10 sm:px-8 sm:py-8">
                <h1 className="text-3xl font-bold text-white mb-3 sm:text-5xl md:text-[2.75rem] leading-tight break-words">
                  About Fikiri Solutions
                </h1>
                <p className="text-lg sm:text-xl text-white/85 mb-4 px-1 sm:px-0 leading-relaxed">
                  Practical automation for teams that run on email and customer conversations.
                </p>
                <p className="text-base sm:text-lg text-white/75 leading-relaxed text-left sm:text-center">
                  We help businesses respond faster, organize customer relationships, and spend less time on repetitive
                  admin. If your team books jobs, handles inbound inquiries, or manages a sales pipeline, Fikiri fits.
                  We stay focused on outcomes that matter: clearer inboxes, reliable follow-up, and tools your staff will
                  actually use.
                </p>
              </div>
            </Reveal>
          </Container>
        </section>

        {/* Main Content */}
        <section className="relative z-10 py-8 sm:py-12 pb-[max(2rem,env(safe-area-inset-bottom))]" aria-labelledby={sectionHeadingId}>
          <Container>
            {/* Services */}
            <Reveal direction="up">
              <h2 id={sectionHeadingId} className="text-2xl font-semibold text-white mb-2">
                What we deliver
              </h2>
              <p className="text-sm text-white/75 mb-6 max-w-2xl">
                Three connected capabilities. Open each card to see where the day-to-day ROI shows up.
              </p>
            </Reveal>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 items-start">
              {serviceCards.map((card, index) => {
                const isOpen = openServiceId === card.id
                const panelId = `${card.id}-panel`
                const headerId = `${card.id}-header`
                const directions = ['left', 'up', 'right'] as const
                return (
                  <Reveal key={card.id} direction={directions[index % 3]} delay={0.08 + index * 0.1}>
                  <article
                    className={cn(
                      'group text-left relative overflow-hidden flex flex-col rounded-2xl bg-white/[0.95] backdrop-blur-sm shadow-md shadow-orange-950/25 ring-1 ring-white/30',
                      'transition-shadow duration-300',
                      isOpen && 'ring-orange-400/50 shadow-lg shadow-orange-500/20'
                    )}
                  >
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/5 via-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <div className="relative w-full aspect-[4/3] min-h-[180px] sm:aspect-[3/4] sm:min-h-[280px]">
                      <img
                        src={card.imageSrc}
                        alt={card.imageAlt}
                        className="absolute inset-0 h-full w-full object-cover object-center"
                        loading="lazy"
                        decoding="async"
                      />
                    </div>
                    <div className="relative flex flex-col border-t border-stone-900/5 bg-gradient-to-b from-white to-stone-50">
                      <h3 className="m-0 text-lg font-semibold text-stone-900">
                        <button
                          type="button"
                          id={headerId}
                          aria-expanded={isOpen}
                          aria-controls={panelId}
                          onClick={() => toggleService(card.id)}
                          className={cn(
                            'w-full max-w-full min-w-0 text-left px-5 pt-4 pb-3 sm:px-6 sm:pt-5 sm:pb-4',
                            'flex items-start gap-3 rounded-none font-inherit text-inherit touch-manipulation',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/80 focus-visible:ring-offset-2 focus-visible:ring-offset-white',
                            '[-webkit-tap-highlight-color:transparent] active:bg-black/[0.03]'
                          )}
                        >
                          <span className="flex-1 min-w-0">
                            <span className="block mb-1.5">{card.title}</span>
                            <span className="block text-stone-700 text-sm font-normal leading-relaxed">
                              {card.teaser}
                            </span>
                            <span className="mt-2 inline-flex items-center text-xs font-medium text-orange-700">
                              {isOpen ? 'Hide details' : 'Learn more'}
                            </span>
                          </span>
                          <ChevronDown
                            className={cn(
                              'h-5 w-5 shrink-0 text-stone-500 mt-0.5 transition-transform duration-300',
                              isOpen && 'rotate-180 text-stone-900'
                            )}
                            aria-hidden
                          />
                        </button>
                      </h3>
                      <div
                        id={panelId}
                        role="region"
                        aria-labelledby={headerId}
                        aria-hidden={!isOpen}
                        className={cn(
                          'grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none',
                          isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
                        )}
                      >
                        <div className="overflow-hidden min-h-0">
                          <div className="px-5 pb-5 pt-0 sm:px-6 sm:pb-6 border-t border-stone-900/5">
                            <ul className="mt-4 space-y-2.5 text-sm text-stone-700 leading-relaxed list-disc pl-4 marker:text-orange-600">
                              {card.details.bullets.map((item, bulletIndex) => (
                                <li key={`${card.id}-${bulletIndex}`}>{item}</li>
                              ))}
                            </ul>
                            <p className="mt-4 text-sm text-stone-900 leading-relaxed border-l-2 border-orange-500/60 pl-3 break-words">
                              {card.details.closing}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                  </Reveal>
                )
              })}
            </div>

            {/* Business Information – moved to bottom with subtle gradient */}
            <Reveal direction="up" delay={0.06}>
            <div className="mt-12 sm:mt-16 bg-white/[0.95] backdrop-blur-sm rounded-2xl border border-white/30 shadow-md shadow-orange-950/20 p-5 sm:p-8 relative overflow-hidden">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-orange-500/10 via-red-500/10 to-transparent opacity-80" />
              <div className="relative grid grid-cols-1 md:grid-cols-2 gap-8">
                <Reveal direction="left" delay={0.1}>
                <div>
                  <h2 className="text-2xl font-semibold text-stone-900 mb-4">
                    Business Information
                  </h2>
                  <h3 className="text-lg font-medium text-stone-900 mb-4">
                    Company Details
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-stone-600">Business Name:</span>
                      <p className="text-stone-900">Fikiri Solutions</p>
                    </div>
                    <div>
                      <span className="font-medium text-stone-600">Industry:</span>
                      <p className="text-stone-900">AI-Powered Business Automation</p>
                    </div>
                    <div>
                      <span className="font-medium text-stone-600">Website:</span>
                      <p className="text-stone-900">https://fikirisolutions.com</p>
                    </div>
                    <div>
                      <span className="font-medium text-stone-600">Email:</span>
                      <p className="text-stone-900">info@fikirisolutions.com</p>
                    </div>
                  </div>
                </div>
                </Reveal>
                <Reveal direction="right" delay={0.18}>
                <div>
                  <h3 className="text-lg font-medium text-stone-900 mb-4">
                    Contact Information
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-stone-600">Location:</span>
                      <p className="text-stone-900">
                        Florida, United States
                      </p>
                    </div>
                  </div>
                </div>
                </Reveal>
              </div>
            </div>
            </Reveal>
          </Container>
        </section>
      </div>
      <MarketingChatWidget />
    </RadiantLayout>
  )
}
