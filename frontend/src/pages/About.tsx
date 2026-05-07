/**
 * About page: one implementation for all viewports (not split mobile/desktop code paths).
 * Tailwind is mobile-first—unprefixed utilities apply to the smallest screens; sm/md/lg add or
 * adjust for larger breakpoints so desktop/content changes stay in sync while mobile stays usable.
 */
import React, { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { ChevronDown, Mail, Sparkles, Users } from 'lucide-react'
import { RadiantLayout, Container, Gradient, AnimatedBackground } from '../components/radiant'
import { PublicChatbotWidget } from '../components/PublicChatbotWidget'
import { getSectorFitPresentation, type FeatureFitId } from '../lib/aboutSectorMatch'
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

const SECTOR_DEBOUNCE_MS = 180

/** One-tap probes across different sector templates—click applies instantly */
const EXAMPLE_BUSINESS_HINTS = [
  'Landscaping and seasonal cleanup',
  'Neighborhood bakery / café',
  'Family dental clinic',
  'MSP / managed IT for SMBs',
  'Staffing agency for healthcare hires',
  'Commercial janitorial contractor',
  'Independent insurance brokerage',
  'Fitness studio memberships',
]

const FEATURE_ICONS: Record<FeatureFitId, LucideIcon> = {
  email_automation: Mail,
  crm_management: Users,
  ai_assistant: Sparkles,
}

function SectorFitExplorer() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const textareaId = useId()
  const resultsId = useId()

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim())
    }, SECTOR_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [query])

  const fit = useMemo(() => getSectorFitPresentation(debouncedQuery), [debouncedQuery])
  const hasTyped = debouncedQuery.length > 0

  const strengthNote =
    !hasTyped
      ? null
      : fit.matchStrength === 'high'
        ? 'Closer keyword alignment — suggestions are tuned to sectors like yours.'
        : fit.matchStrength === 'medium'
          ? 'Partial match — add a bit more sector detail to sharpen suggestions.'
          : 'General pattern — useful if your niche is uncommon or overlaps several categories.'

  return (
    <div className="rounded-2xl border border-border/80 bg-card/85 backdrop-blur-sm shadow-lg shadow-stone-900/5 overflow-hidden relative max-w-full">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/[0.07] via-transparent to-sky-500/[0.06]" />
      <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-0 lg:divide-x lg:divide-border/60">
        <div className="lg:col-span-5 p-5 sm:p-8 flex flex-col gap-5 border-b lg:border-b-0 border-border/60 pb-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Step 1</p>
            <label htmlFor={textareaId} className="text-base font-semibold text-foreground block mb-2">
              Tell us what your business does
            </label>
            <p id={`${textareaId}-hint`} className="text-sm text-muted-foreground mb-3 leading-relaxed">
              Use plain language: what you sell, who you serve, and how leads usually come in (e.g. emergency
              plumbing, med-spa consultations).
            </p>
            <textarea
              id={textareaId}
              aria-describedby={`${textareaId}-hint`}
              rows={5}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. we run a small HVAC company…"
              autoComplete="off"
              enterKeyHint="done"
              className={cn(
                // text-base below sm prevents iOS zoom-on-focus when font size would be under 16px
                'w-full max-w-full resize-y rounded-xl border border-border bg-background/80 px-4 py-3 text-base leading-relaxed sm:text-sm',
                'placeholder:text-muted-foreground/70 touch-manipulation',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background'
              )}
              spellCheck
            />
            <div className="flex flex-wrap gap-2 mt-4">
              <span className="text-xs text-muted-foreground w-full pt-1 sm:inline sm:w-auto sm:mr-1 sm:pt-0">Examples:</span>
              {EXAMPLE_BUSINESS_HINTS.map((hint) => (
                <button
                  key={hint}
                  type="button"
                  aria-label={`Use example: ${hint}`}
                  onClick={() => {
                    setQuery(hint)
                    setDebouncedQuery(hint.trim())
                  }}
                  className={cn(
                    'text-xs font-medium px-4 py-2.5 sm:py-1.5 sm:px-3 rounded-full text-left',
                    'min-h-11 sm:min-h-0 bg-muted/70 hover:bg-muted active:bg-muted/90 text-foreground border border-border/80 transition-colors touch-manipulation',
                    '[-webkit-tap-highlight-color:transparent]'
                  )}
                >
                  <span className="break-words">{hint}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-7 p-5 sm:p-8 flex flex-col min-h-[240px] sm:min-h-[280px]">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Step 2</p>
          <h3 className="text-lg font-semibold text-foreground mb-3">How Fikiri can help</h3>
          <div
            id={resultsId}
            className={cn(
              'flex-1 rounded-xl border border-border/70 bg-background/55 px-4 py-5 sm:px-5 sm:py-6 max-w-full min-w-0',
              hasTyped && fit.matchStrength === 'high' && 'ring-2 ring-orange-500/35',
              hasTyped && fit.matchStrength === 'medium' && 'ring-1 ring-amber-500/35'
            )}
            aria-live="polite"
            aria-atomic="true"
          >
            <p className="text-sm font-semibold text-foreground mb-2 break-words hyphens-none">{fit.headline}</p>
            {strengthNote !== null ? (
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">{strengthNote}</p>
            ) : (
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
                Use an example or type your own description to see where Fikiri can add value first.
              </p>
            )}
            <p className="text-sm text-muted-foreground leading-relaxed mb-6 break-words">{fit.summary}</p>
            <ul className="space-y-5">
              {fit.featuresOrdered.map((row) => {
                const Icon = FEATURE_ICONS[row.id]
                return (
                  <li key={row.id} className="flex gap-3 min-w-0">
                    <span className="mt-0.5 flex h-10 w-10 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 ring-1 ring-orange-500/20">
                      <Icon className="h-5 w-5 text-orange-600 dark:text-orange-400" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-foreground break-words">{row.title}</p>
                      <p className="text-sm text-muted-foreground mt-1 leading-relaxed break-words">{row.fit}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
            <div className="mt-8 pt-5 border-t border-border/70">
              <p className="text-sm text-muted-foreground mb-3">
                Want a tailored game plan for your exact workflow? Speak with our team and get practical next steps.
              </p>
              <Link
                to="/contact"
                className={cn(
                  'inline-flex min-h-11 min-w-[44px] items-center text-sm font-semibold text-orange-600 hover:text-orange-500',
                  'dark:text-orange-400 dark:hover:text-orange-300 underline underline-offset-2 py-2 -my-2 sm:min-h-0 sm:py-0 sm:my-0 touch-manipulation',
                  '[-webkit-tap-highlight-color:transparent]'
                )}
              >
                Talk to us
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export const About: React.FC = () => {
  const [openServiceId, setOpenServiceId] = useState<string | null>(null)
  const sectionHeadingId = useId()
  const sectorMatchSectionId = useId()

  const toggleService = useCallback((id: string) => {
    setOpenServiceId((prev) => (prev === id ? null : id))
  }, [])

  return (
    <RadiantLayout>
      <div className="min-h-screen bg-background text-foreground relative">
        <div className="absolute inset-0 fikiri-gradient-animated">
          <AnimatedBackground />
        </div>
        {/* Hero */}
        <section className="relative py-12 sm:py-20 z-10">
          <Gradient className="absolute inset-x-2 top-0 bottom-0 rounded-3xl ring-1 ring-black/5 ring-inset opacity-20" />
          <Container className="relative">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-3xl font-bold text-foreground mb-4 sm:text-5xl md:text-[2.75rem] leading-tight break-words">
                About Fikiri Solutions
              </h1>
              <p className="text-lg sm:text-xl text-muted-foreground mb-6 px-1 sm:px-0 leading-relaxed">
                Practical automation for teams that run on email and customer conversations.
              </p>
              <p className="text-base sm:text-lg text-muted-foreground leading-relaxed text-left sm:text-center">
                We help businesses respond faster, organize customer relationships, and spend less time on repetitive
                admin. If your team books jobs, handles inbound inquiries, or manages a sales pipeline, Fikiri fits.
                We stay focused on outcomes that matter: clearer inboxes, reliable follow-up, and tools your staff will
                actually use.
              </p>
            </div>
          </Container>
        </section>

        {/* Main Content */}
        <section className="py-10 sm:py-16 relative z-10 pb-[max(2.5rem,env(safe-area-inset-bottom))]" aria-labelledby={sectionHeadingId}>
          <Container>
            {/* Services */}
            <h2 id={sectionHeadingId} className="text-2xl font-semibold text-foreground mb-2">
              What we deliver
            </h2>
            <p className="text-sm text-muted-foreground mb-8 max-w-2xl">
              Three connected capabilities. Open each card to see where the day-to-day ROI shows up.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 items-start">
              {serviceCards.map((card) => {
                const isOpen = openServiceId === card.id
                const panelId = `${card.id}-panel`
                const headerId = `${card.id}-header`
                return (
                  <article
                    key={card.id}
                    className={cn(
                      'group text-left relative overflow-hidden flex flex-col rounded-2xl bg-card/40 backdrop-blur-sm shadow-md shadow-stone-900/8 ring-1 ring-stone-900/6 dark:ring-white/8',
                      'transition-shadow duration-300',
                      isOpen && 'ring-orange-500/40 shadow-lg shadow-orange-500/10'
                    )}
                  >
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/5 via-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <div className="relative w-full aspect-[3/4] min-h-[220px] sm:min-h-[280px]">
                      <img
                        src={card.imageSrc}
                        alt={card.imageAlt}
                        className="absolute inset-0 h-full w-full object-cover object-center"
                        loading="lazy"
                        decoding="async"
                      />
                    </div>
                    <div className="relative flex flex-col border-t border-stone-900/5 bg-gradient-to-b from-card/30 to-card/50 dark:border-white/5 dark:from-white/[0.04] dark:to-white/[0.07]">
                      <h3 className="m-0 text-lg font-semibold text-foreground">
                        <button
                          type="button"
                          id={headerId}
                          aria-expanded={isOpen}
                          aria-controls={panelId}
                          onClick={() => toggleService(card.id)}
                          className={cn(
                            'w-full max-w-full min-w-0 text-left px-5 pt-4 pb-3 sm:px-6 sm:pt-5 sm:pb-4',
                            'flex items-start gap-3 rounded-none font-inherit text-inherit touch-manipulation',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/80 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                            '[-webkit-tap-highlight-color:transparent] active:bg-black/[0.03] dark:active:bg-white/[0.04]'
                          )}
                        >
                          <span className="flex-1 min-w-0">
                            <span className="block mb-1.5">{card.title}</span>
                            <span className="block text-muted-foreground text-sm font-normal leading-relaxed">
                              {card.teaser}
                            </span>
                            <span className="mt-2 inline-flex items-center text-xs font-medium text-orange-600 dark:text-orange-400">
                              {isOpen ? 'Hide details' : 'Learn more'}
                            </span>
                          </span>
                          <ChevronDown
                            className={cn(
                              'h-5 w-5 shrink-0 text-muted-foreground mt-0.5 transition-transform duration-300',
                              isOpen && 'rotate-180 text-foreground'
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
                          <div className="px-5 pb-5 pt-0 sm:px-6 sm:pb-6 border-t border-stone-900/5 dark:border-white/5">
                            <ul className="mt-4 space-y-2.5 text-sm text-muted-foreground leading-relaxed list-disc pl-4 marker:text-orange-500/80">
                              {card.details.bullets.map((item, bulletIndex) => (
                                <li key={`${card.id}-${bulletIndex}`}>{item}</li>
                              ))}
                            </ul>
                            <p className="mt-4 text-sm text-foreground/90 leading-relaxed border-l-2 border-orange-500/50 pl-3 break-words">
                              {card.details.closing}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>

            <section aria-labelledby={sectorMatchSectionId} className="pt-8 border-t border-border/50 overflow-x-hidden">
              <h2 id={sectorMatchSectionId} className="text-xl sm:text-2xl font-semibold text-foreground mb-2 leading-tight break-words">
                See how Fikiri fits your sector
              </h2>
              <p className="text-sm text-muted-foreground mb-2 max-w-3xl leading-relaxed break-words">
                Describe your business in your own words. We map it to the Email Automation, CRM Management, and AI
                Assistant workflows that typically deliver value first for teams like yours. Use this as a quick way to
                start the right conversation with us.
              </p>
              <p className="text-xs text-muted-foreground mb-8 max-w-2xl leading-relaxed">
                This is a fast directional guide, not formal consulting. We can validate the recommendations with your
                team in a short call.
              </p>
              <SectorFitExplorer />
            </section>

            {/* Business Information – moved to bottom with subtle gradient */}
            <div className="mt-12 sm:mt-16 bg-card/95 backdrop-blur-sm rounded-2xl border border-border/80 shadow-sm p-5 sm:p-8 relative overflow-hidden">
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
