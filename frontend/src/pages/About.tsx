/**
 * About page: consulting-first narrative (why → how → what → principles → examples → action).
 * One implementation for all viewports. Does not host Sector Fit.
 */
import React, { useCallback, useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'
import { RadiantLayout, Container, Reveal, Subheading } from '../components/radiant'
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

const processSteps = [
  {
    num: '01',
    title: 'Understand the workflow',
    body: 'We map the actual process, not the idealized one.',
  },
  {
    num: '02',
    title: 'Find the friction',
    body: 'We identify delays, handoff problems, repetitive admin, missed follow-up, and disconnected systems.',
  },
  {
    num: '03',
    title: 'Build around the business',
    body: 'We design automation, CRM, AI, or software around the existing operation.',
  },
  {
    num: '04',
    title: 'Refine and hand off',
    body: 'We test, simplify, document, and leave the business with something the team can actually use.',
  },
] as const

const principles = [
  {
    title: 'Consulting before software',
    body: 'We do not force a tool onto a workflow we have not understood.',
  },
  {
    title: 'Practical before impressive',
    body: 'A smaller system that works is more useful than an overbuilt platform nobody uses.',
  },
  {
    title: 'Connected, not fragmented',
    body: 'Email, CRM, AI, forms, scheduling, and operations should work together.',
  },
  {
    title: 'Built to operate',
    body: 'We care about what happens after launch: reliability, handoff, usability, and maintenance.',
  },
] as const

const practiceFlows = [
  {
    title: 'Lead follow-up',
    steps: ['Inquiry', 'CRM record', 'Staff alert', 'Follow-up', 'Activity logged'],
  },
  {
    title: 'Customer operations',
    steps: ['Request or appointment', 'Workflow', 'Reminder', 'Staff handoff', 'Completion tracking'],
  },
  {
    title: 'AI-assisted work',
    steps: ['Incoming message', 'Context', 'Suggested response', 'Human review'],
  },
] as const

const EASE = [0.22, 1, 0.36, 1] as const

/** Faint baobab/network branch motif — decorative only, distinct from homepage tree hero. */
function AboutHeroMotif() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.45]"
      viewBox="0 0 800 420"
      fill="none"
      aria-hidden
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <radialGradient id="about-node-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#E7641C" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#E7641C" stopOpacity="0" />
        </radialGradient>
      </defs>
      {/* Soft glow pools */}
      <circle cx="620" cy="120" r="90" fill="url(#about-node-glow)" opacity="0.35" />
      <circle cx="180" cy="280" r="70" fill="url(#about-node-glow)" opacity="0.25" />
      {/* Branch / network lines */}
      <g stroke="#E7641C" strokeOpacity="0.28" strokeWidth="1.25">
        <path d="M120 340 C200 280, 260 220, 340 180 C400 150, 480 140, 560 110" />
        <path d="M340 180 C380 240, 420 260, 490 300" />
        <path d="M340 180 C300 140, 240 100, 200 70" />
        <path d="M560 110 C600 160, 640 200, 700 240" />
        <path d="M560 110 C620 80, 680 60, 740 50" />
        <path d="M490 300 C530 280, 580 250, 620 220" />
      </g>
      {/* Nodes */}
      <g fill="#F39C12">
        <circle cx="340" cy="180" r="3.5" opacity="0.7" />
        <circle cx="560" cy="110" r="3" opacity="0.65" />
        <circle cx="490" cy="300" r="2.5" opacity="0.55" />
        <circle cx="200" cy="70" r="2.5" opacity="0.5" />
        <circle cx="700" cy="240" r="2.5" opacity="0.5" />
        <circle cx="120" cy="340" r="2" opacity="0.4" />
      </g>
      {/* Outer rings on primary nodes */}
      <circle cx="340" cy="180" r="10" stroke="#E7641C" strokeOpacity="0.2" strokeWidth="1" />
      <circle cx="560" cy="110" r="8" stroke="#E7641C" strokeOpacity="0.18" strokeWidth="1" />
    </svg>
  )
}

function ProcessTimeline() {
  const reduceMotion = useReducedMotion()

  return (
    <ol className="relative grid grid-cols-1 gap-7 md:grid-cols-4 md:gap-6">
      {/* Desktop connector line */}
      <div
        className="pointer-events-none absolute left-0 right-0 top-[1.125rem] hidden h-px md:block"
        aria-hidden
      >
        <motion.div
          className="h-full origin-left bg-gradient-to-r from-orange-500/70 via-amber-500/50 to-orange-500/20"
          initial={reduceMotion ? false : { scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: reduceMotion ? 0 : 0.9, ease: EASE, delay: 0.1 }}
        />
      </div>

      {processSteps.map((step, index) => (
        <Reveal key={step.num} direction="up" delay={0.08 + index * 0.1} distance={12}>
          <li className="relative flex gap-3.5 md:flex-col md:gap-3">
            {/* Mobile vertical connector */}
            {index < processSteps.length - 1 && (
              <span
                className="absolute left-[0.9rem] top-9 bottom-[-1.25rem] w-px bg-gradient-to-b from-orange-500/50 to-orange-500/10 md:hidden"
                aria-hidden
              />
            )}
            <motion.span
              className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-orange-400/40 bg-[#1c1510] text-[11px] font-semibold tracking-wide text-orange-300 shadow-[0_0_16px_rgba(231,100,28,0.25)]"
              initial={reduceMotion ? false : { boxShadow: '0 0 0 rgba(231,100,28,0)' }}
              whileInView={{
                boxShadow: '0 0 16px rgba(231,100,28,0.35)',
              }}
              viewport={{ once: true, amount: 0.6 }}
              transition={{ duration: 0.45, delay: reduceMotion ? 0 : 0.15 + index * 0.12 }}
            >
              {step.num}
            </motion.span>
            <div className="min-w-0 pt-0.5 md:pt-1">
              <h3 className="font-serif text-base font-medium tracking-tight text-white sm:text-xl">
                {step.title}
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-white/70 sm:mt-2 sm:text-[0.95rem]">
                {step.body}
              </p>
            </div>
          </li>
        </Reveal>
      ))}
    </ol>
  )
}

function WorkflowNodes({ steps }: { steps: readonly string[] }) {
  const reduceMotion = useReducedMotion()
  // Avoid opacity:0 whileInView chips on mobile — same iOS stuck-invisible failure mode as nav.
  const skipHide =
    reduceMotion ||
    (typeof window !== 'undefined' &&
      window.matchMedia?.('(max-width: 639px)')?.matches === true)

  return (
    <ol className="mt-3.5 flex flex-col gap-1 sm:mt-4 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-1.5 sm:gap-y-2">
      {steps.map((label, index) => (
        <li key={`${label}-${index}`} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-1.5">
          <motion.span
            className="inline-flex w-fit max-w-full rounded-md border border-white/10 bg-white/[0.06] px-2.5 py-1.5 text-xs leading-snug text-white/85 sm:text-[0.8rem]"
            initial={skipHide ? false : { opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.35, delay: skipHide ? 0 : index * 0.06, ease: EASE }}
          >
            {label}
          </motion.span>
          {index < steps.length - 1 && (
            <>
              <span className="pl-3 text-[0.7rem] leading-none text-orange-400/55 sm:hidden" aria-hidden>
                ↓
              </span>
              <span className="hidden text-orange-400/60 sm:inline" aria-hidden>
                →
              </span>
            </>
          )}
        </li>
      ))}
    </ol>
  )
}

export const About: React.FC = () => {
  const [openServiceId, setOpenServiceId] = useState<string | null>(null)
  const systemsHeadingId = useId()
  const processHeadingId = useId()
  const principlesHeadingId = useId()
  const practiceHeadingId = useId()

  const toggleService = useCallback((id: string) => {
    setOpenServiceId((prev) => (prev === id ? null : id))
  }, [])

  return (
    <RadiantLayout>
      <div className="relative min-h-dvh overflow-x-hidden pb-[max(7rem,calc(env(safe-area-inset-bottom)+5.5rem))] sm:pb-[env(safe-area-inset-bottom)]">
        {/* 1. Why Fikiri hero */}
        <section
          className="relative z-10 overflow-hidden pb-10 pt-10 sm:pb-14 sm:pt-14 md:pb-16 md:pt-16"
          aria-labelledby="about-hero-heading"
        >
          <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
            <AboutHeroMotif />
          </div>
          <Container className="relative">
            <Reveal direction="up" distance={14}>
              <div className="mx-auto max-w-3xl text-center">
                <Subheading dark className="mb-3 sm:mb-4">
                  Why Fikiri
                </Subheading>
                <h1
                  id="about-hero-heading"
                  className="font-serif text-[1.75rem] font-medium leading-snug tracking-tight text-pretty text-white sm:text-5xl sm:leading-tight md:text-[3rem] md:leading-[1.12]"
                >
                  We build systems around how your business actually works.
                </h1>
                <p className="mx-auto mt-4 max-w-2xl text-[0.95rem] leading-relaxed text-white/75 sm:mt-6 sm:text-lg">
                  Fikiri Solutions starts with the workflow, not the software. We learn where time is
                  lost, where customers fall through, and where repetitive work slows the team
                  down—then build practical systems around those gaps.
                </p>
              </div>
            </Reveal>
          </Container>
        </section>

        {/* 2. How we work */}
        <section
          className="relative z-10 py-10 sm:py-14"
          aria-labelledby={processHeadingId}
        >
          <Container>
            <Reveal direction="up" distance={12}>
              <Subheading dark className="mb-3">
                Process
              </Subheading>
              <h2
                id={processHeadingId}
                className="font-serif text-2xl font-medium tracking-tight text-white sm:text-4xl"
              >
                How we work
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/70 sm:text-base">
                A consulting-first sequence: understand the operation, then build only what the
                workflow needs.
              </p>
            </Reveal>
            <div className="mt-10 sm:mt-12">
              <ProcessTimeline />
            </div>
          </Container>
        </section>

        {/* 3. Capability cards — tools that follow from the process */}
        <section
          className="relative z-10 overflow-x-clip py-10 sm:py-14"
          aria-labelledby={systemsHeadingId}
        >
          <Container>
            <Reveal direction="up" distance={12}>
              <Subheading dark className="mb-3">
                Capabilities
              </Subheading>
              <h2
                id={systemsHeadingId}
                className="font-serif text-2xl font-medium tracking-tight text-white sm:text-4xl"
              >
                The systems we build around that process
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/70 sm:text-base">
                Different businesses need different combinations. We use the pieces that solve the
                actual workflow problem.
              </p>
            </Reveal>

            <div className="mt-8 grid grid-cols-1 items-start gap-6 sm:gap-8 md:mt-10 md:grid-cols-3">
              {serviceCards.map((card, index) => {
                const isOpen = openServiceId === card.id
                const panelId = `${card.id}-panel`
                const headerId = `${card.id}-header`
                return (
                  <Reveal
                    key={card.id}
                    direction="up"
                    delay={0.06 + index * 0.08}
                    distance={12}
                  >
                    <article
                      className={cn(
                        'group relative flex flex-col overflow-hidden rounded-2xl bg-white/[0.95] text-left shadow-md shadow-orange-950/25 ring-1 ring-white/30 backdrop-blur-sm',
                        'transition-shadow duration-300',
                        isOpen && 'ring-orange-400/50 shadow-lg shadow-orange-500/20'
                      )}
                    >
                      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-500/5 via-amber-500/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                      {/* Portrait crop only in 3-col layout — avoid overly tall single-column cards */}
                      <div className="relative aspect-[4/3] min-h-[160px] w-full md:aspect-[3/4] md:min-h-[280px]">
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
                              'w-full min-w-0 max-w-full touch-manipulation px-5 pb-3 pt-4 text-left font-inherit text-inherit sm:px-6 sm:pb-4 sm:pt-5',
                              'rounded-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/80 focus-visible:ring-offset-2 focus-visible:ring-offset-white',
                              '[-webkit-tap-highlight-color:transparent] active:bg-black/[0.03]'
                            )}
                          >
                            <span className="flex items-start gap-3">
                              <span className="min-w-0 flex-1">
                                <span className="mb-1.5 block">{card.title}</span>
                                <span className="block text-sm font-normal leading-relaxed text-stone-700">
                                  {card.teaser}
                                </span>
                                <span className="mt-2 inline-flex items-center text-xs font-medium text-orange-700">
                                  {isOpen ? 'Hide details' : 'Learn more'}
                                </span>
                              </span>
                              <ChevronDown
                                className={cn(
                                  'mt-0.5 h-5 w-5 shrink-0 text-stone-500 transition-transform duration-300',
                                  isOpen && 'rotate-180 text-stone-900'
                                )}
                                aria-hidden
                              />
                            </span>
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
                          <div className="min-h-0 overflow-hidden">
                            <div className="border-t border-stone-900/5 px-5 pb-5 pt-0 sm:px-6 sm:pb-6">
                              <ul className="mt-4 list-disc space-y-2.5 pl-4 text-sm leading-relaxed text-stone-700 marker:text-orange-600">
                                {card.details.bullets.map((item, bulletIndex) => (
                                  <li key={`${card.id}-${bulletIndex}`}>{item}</li>
                                ))}
                              </ul>
                              <p className="mt-4 break-words border-l-2 border-orange-500/60 pl-3 text-sm leading-relaxed text-stone-900">
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
          </Container>
        </section>

        {/* 4. What makes Fikiri different */}
        <section
          className="relative z-10 py-10 sm:py-14"
          aria-labelledby={principlesHeadingId}
        >
          <Container>
            <Reveal direction="up" distance={12}>
              <Subheading dark className="mb-3">
                Principles
              </Subheading>
              <h2
                id={principlesHeadingId}
                className="font-serif text-2xl font-medium tracking-tight text-white sm:text-4xl"
              >
                What makes Fikiri different
              </h2>
            </Reveal>

            <div className="mt-8 grid grid-cols-1 gap-0 border-t border-white/10 sm:mt-10 md:grid-cols-2">
              {principles.map((principle, index) => (
                <Reveal
                  key={principle.title}
                  direction="up"
                  delay={0.05 + index * 0.07}
                  distance={12}
                  className="min-w-0"
                >
                  <div
                    className={cn(
                      'h-full border-b border-white/10 py-5 sm:py-7',
                      index % 2 === 0 ? 'md:border-r md:pr-8' : 'md:pl-8',
                      index >= 2 && 'md:border-b-0'
                    )}
                  >
                    <p className="text-[11px] font-semibold tracking-[0.16em] text-orange-300/80">
                      {String(index + 1).padStart(2, '0')}
                    </p>
                    <h3 className="mt-2 font-serif text-lg font-medium tracking-tight text-white sm:text-xl">
                      {principle.title}
                    </h3>
                    <p className="mt-2 max-w-md text-sm leading-relaxed text-white/70 sm:text-[0.95rem]">
                      {principle.body}
                    </p>
                  </div>
                </Reveal>
              ))}
            </div>
          </Container>
        </section>

        {/* 5. What this looks like in practice */}
        <section
          className="relative z-10 py-10 sm:py-14"
          aria-labelledby={practiceHeadingId}
        >
          <Container>
            <Reveal direction="up" distance={12}>
              <Subheading dark className="mb-3">
                In practice
              </Subheading>
              <h2
                id={practiceHeadingId}
                className="font-serif text-2xl font-medium tracking-tight text-white sm:text-4xl"
              >
                What this looks like in practice
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/70 sm:text-base">
                Simple connected flows—not architecture diagrams. This is how the work tends to
                move once systems are in place.
              </p>
            </Reveal>

            <div className="mt-8 grid grid-cols-1 gap-4 sm:mt-10 sm:gap-5 lg:grid-cols-3 lg:gap-6">
              {practiceFlows.map((flow, index) => (
                <Reveal
                  key={flow.title}
                  direction="up"
                  delay={0.06 + index * 0.08}
                  distance={12}
                >
                  <article className="rounded-2xl border border-white/10 bg-black/25 px-4 py-4 backdrop-blur-sm sm:px-6 sm:py-6">
                    <h3 className="font-serif text-base font-medium tracking-tight text-white sm:text-lg">
                      {flow.title}
                    </h3>
                    <WorkflowNodes steps={flow.steps} />
                  </article>
                </Reveal>
              ))}
            </div>
          </Container>
        </section>

        {/* 6. Company at a glance — quiet strip */}
        <section className="relative z-10 py-8 sm:py-10" aria-label="Company at a glance">
          <Container>
            <Reveal direction="up" distance={10}>
              <p className="mx-auto flex max-w-3xl flex-col items-center gap-2 text-center text-sm text-white/70 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-x-2.5 sm:gap-y-1.5 sm:text-[0.95rem]">
                <span>Florida-based</span>
                <span className="hidden text-orange-400/40 sm:inline" aria-hidden>
                  ·
                </span>
                <span>AI automation &amp; software consulting</span>
                <span className="hidden text-orange-400/40 sm:inline" aria-hidden>
                  ·
                </span>
                <a
                  href="https://fikirisolutions.com"
                  className="text-white/70 underline-offset-2 transition-colors hover:text-orange-300 hover:underline"
                >
                  fikirisolutions.com
                </a>
                <span className="hidden text-orange-400/40 sm:inline" aria-hidden>
                  ·
                </span>
                <a
                  href="mailto:info@fikirisolutions.com"
                  className="text-white/70 underline-offset-2 transition-colors hover:text-orange-300 hover:underline"
                >
                  info@fikirisolutions.com
                </a>
              </p>
            </Reveal>
          </Container>
        </section>
      </div>
      <MarketingChatWidget />
    </RadiantLayout>
  )
}
