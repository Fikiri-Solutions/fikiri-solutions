import { useCallback, useEffect, useId, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Container } from './Container'
import { Button } from './Button'
import { Heading, Subheading } from './Text'
import { Reveal } from './Reveal'
import { clientPartnerships, type ClientPartnership } from '@/lib/clientPartnerships'
import { cn } from '@/lib/utils'

const AUTOPLAY_MS = 6000

function ClientLogoFallback({
  logoAlt,
  fallbackMark,
}: {
  logoAlt: string
  fallbackMark: string
}) {
  return (
    <div
      className="flex h-24 w-full items-center justify-center rounded-xl bg-gradient-to-br from-orange-500/15 via-amber-500/10 to-transparent ring-1 ring-orange-500/20 sm:h-28"
      role="img"
      aria-label={logoAlt}
    >
      <span className="font-mono text-2xl font-semibold tracking-widest text-orange-700">
        {fallbackMark}
      </span>
    </div>
  )
}

function ClientLogo({
  logoSrc,
  logoAlt,
  fallbackMark,
  darkLogoPlate,
}: {
  logoSrc?: string
  logoAlt: string
  fallbackMark: string
  darkLogoPlate?: boolean
}) {
  const [failed, setFailed] = useState(false)

  if (!logoSrc || failed) {
    return <ClientLogoFallback logoAlt={logoAlt} fallbackMark={fallbackMark} />
  }

  return (
    <div
      className={
        darkLogoPlate
          ? 'flex h-24 w-full items-center justify-center overflow-hidden rounded-xl bg-black p-3 ring-1 ring-white/10 sm:h-28 sm:p-4'
          : 'flex h-24 w-full items-center justify-center overflow-hidden rounded-xl bg-white p-3 ring-1 ring-black/10 sm:h-28 sm:p-4'
      }
    >
      <img
        src={logoSrc}
        alt={logoAlt}
        className="h-full w-full object-contain"
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
      />
    </div>
  )
}

function PartnershipCard({
  client,
  reduceMotion,
}: {
  client: ClientPartnership
  reduceMotion: boolean | null
}) {
  return (
    <article
      className={cn(
        'group flex h-full min-h-[22rem] flex-col rounded-2xl bg-white/[0.95] p-6 shadow-md shadow-orange-950/20 ring-1 ring-white/30 backdrop-blur-sm transition-shadow duration-300',
        !reduceMotion && 'hover:shadow-lg hover:shadow-brand-primary/25 hover:ring-brand-primary/40'
      )}
    >
      <ClientLogo
        logoSrc={client.logoSrc}
        logoAlt={client.logoAlt}
        fallbackMark={client.fallbackMark}
        darkLogoPlate={client.darkLogoPlate}
      />
      <h3 className="mt-5 text-lg font-semibold tracking-tight text-stone-900">{client.name}</h3>
      <p className="mt-1 text-sm font-medium text-orange-700">{client.category}</p>
      <p className="mt-3 flex-1 text-sm leading-relaxed text-stone-600">{client.summary}</p>
      <a
        href={client.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-5 inline-flex min-h-[44px] items-center text-sm font-medium text-brand-primary transition-colors group-hover:text-fikiri-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/80 focus-visible:ring-offset-2"
      >
        Visit site
        <span className="sr-only"> ({client.name})</span>
        <span aria-hidden className="ml-1 transition-transform duration-200 group-hover:translate-x-0.5">
          →
        </span>
      </a>
    </article>
  )
}

function usePerView(): number {
  const [perView, setPerView] = useState(1)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    const update = () => setPerView(mq.matches ? 2 : 1)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return perView
}

export function ClientPartnerships() {
  const reduceMotion = useReducedMotion()
  const perView = usePerView()
  const statusId = useId()
  const total = clientPartnerships.length
  const pageCount = Math.max(1, Math.ceil(total / perView))

  const [page, setPage] = useState(0)
  const [paused, setPaused] = useState(false)
  const [direction, setDirection] = useState(1)

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount - 1))
  }, [pageCount])

  const goTo = useCallback(
    (nextPage: number, dir: number) => {
      setDirection(dir)
      setPage(((nextPage % pageCount) + pageCount) % pageCount)
    },
    [pageCount]
  )

  const goNext = useCallback(() => {
    goTo(page + 1, 1)
  }, [goTo, page])

  const goPrev = useCallback(() => {
    goTo(page - 1, -1)
  }, [goTo, page])

  useEffect(() => {
    if (reduceMotion || paused || pageCount <= 1) return
    const id = window.setInterval(() => {
      setDirection(1)
      setPage((current) => (current + 1) % pageCount)
    }, AUTOPLAY_MS)
    return () => window.clearInterval(id)
  }, [reduceMotion, paused, pageCount, page])

  const visibleClients = clientPartnerships.slice(page * perView, page * perView + perView)
  const slideLabel = `Showing partnerships ${page * perView + 1} to ${Math.min(
    page * perView + visibleClients.length,
    total
  )} of ${total}`

  return (
    <section
      className="relative overflow-hidden py-14 sm:py-16 lg:py-20"
      id="client-partnerships"
      aria-labelledby="client-partnerships-heading"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand-primary/40 to-transparent"
        aria-hidden
      />

      <Container className="relative">
        <Reveal>
          <Subheading dark>Client Partnerships</Subheading>
          <Heading as="h2" dark id="client-partnerships-heading" className="mt-2 max-w-3xl">
            Real client work across different industries.
          </Heading>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-white/80 sm:mt-4 sm:text-lg">
            Fikiri starts with consulting and workflow discovery. From there, we help businesses
            plan, build, and support practical systems around their real operations — from
            automation and CRM to product workflows, cloud support, and custom tools.
          </p>
        </Reveal>

        <div
          className="relative mt-8 sm:mt-10"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          <div
            className="overflow-hidden"
            role="region"
            aria-roledescription="carousel"
            aria-label="Client partnership cards"
            aria-describedby={statusId}
          >
            <p id={statusId} className="sr-only" aria-live="polite">
              {slideLabel}
            </p>

            <AnimatePresence mode="wait" custom={direction} initial={false}>
              <motion.div
                key={`${page}-${perView}`}
                custom={direction}
                initial={
                  reduceMotion
                    ? false
                    : { opacity: 0, x: direction > 0 ? 36 : -36 }
                }
                animate={{ opacity: 1, x: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, x: direction > 0 ? -36 : 36 }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                className={cn(
                  'grid gap-5',
                  perView === 2 ? 'md:grid-cols-2' : 'grid-cols-1'
                )}
              >
                {visibleClients.map((client) => (
                  <PartnershipCard key={client.name} client={client} reduceMotion={reduceMotion} />
                ))}
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mt-6 flex items-center justify-between gap-3 sm:mt-8">
            <button
              type="button"
              onClick={goPrev}
              aria-label="Previous client partnership"
              className="inline-flex size-11 items-center justify-center rounded-full border border-white/20 bg-white/10 text-white shadow-sm backdrop-blur-sm transition-colors hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-[#1c1510]"
            >
              <ChevronLeft className="h-5 w-5" aria-hidden />
            </button>

            <div className="flex flex-1 flex-col items-center gap-2">
              <div className="flex items-center gap-2" role="tablist" aria-label="Partnership slides">
                {Array.from({ length: pageCount }, (_, index) => {
                  const selected = index === page
                  return (
                    <button
                      key={index}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      aria-label={`Go to partnership slide ${index + 1} of ${pageCount}`}
                      onClick={() => goTo(index, index > page ? 1 : -1)}
                      className={cn(
                        'h-2.5 rounded-full transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-[#1c1510]',
                        selected
                          ? 'w-7 bg-orange-400 shadow-[0_0_12px_rgba(251,146,60,0.55)]'
                          : 'w-2.5 bg-white/35 hover:bg-white/55'
                      )}
                    />
                  )
                })}
              </div>
              <p className="text-xs font-medium text-white/70" aria-hidden>
                {page + 1} of {pageCount}
              </p>
            </div>

            <button
              type="button"
              onClick={goNext}
              aria-label="Next client partnership"
              className="inline-flex size-11 items-center justify-center rounded-full border border-white/20 bg-white/10 text-white shadow-sm backdrop-blur-sm transition-colors hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-[#1c1510]"
            >
              <ChevronRight className="h-5 w-5" aria-hidden />
            </button>
          </div>
        </div>

        {/* Always expose all partnership names/links for assistive discovery */}
        <ul className="sr-only">
          {clientPartnerships.map((client) => (
            <li key={`sr-${client.name}`}>
              <a href={client.url} target="_blank" rel="noopener noreferrer">
                {client.name} — Visit site
              </a>
            </li>
          ))}
        </ul>

        <Reveal delay={0.12} className="mt-10 sm:mt-12">
          <div className="flex flex-col items-start gap-3 sm:items-center sm:text-center">
            <p className="max-w-2xl text-base font-medium text-white sm:text-lg">
              Have a workflow, customer follow-up, or software problem you are trying to solve?
            </p>
            <Button to="/intake">Start a workflow conversation</Button>
          </div>
        </Reveal>
      </Container>
    </section>
  )
}
