import { useEffect, useId, useRef, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { Container } from './Container'
import { Button } from './Button'
import { Heading, Subheading } from './Text'
import { Reveal } from './Reveal'
import { clientPartnerships, type ClientPartnership } from '@/lib/clientPartnerships'
import { cn } from '@/lib/utils'

/** Seconds for one full loop of the duplicated track (RTL conveyor). */
const LOOP_SECONDS = 28

function ClientLogoFallback({
  logoAlt,
  fallbackMark,
}: {
  logoAlt: string
  fallbackMark: string
}) {
  return (
    <div
      className="flex h-16 w-full items-center justify-center rounded-lg bg-gradient-to-br from-orange-500/15 via-amber-500/10 to-transparent ring-1 ring-orange-500/20"
      role="img"
      aria-label={logoAlt}
    >
      <span className="text-lg font-semibold tracking-widest text-orange-700">
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
          ? 'flex h-16 w-full items-center justify-center overflow-hidden rounded-lg bg-black p-2.5 ring-1 ring-white/10'
          : 'flex h-16 w-full items-center justify-center overflow-hidden rounded-lg bg-white p-2.5 ring-1 ring-black/10'
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
  className,
}: {
  client: ClientPartnership
  className?: string
}) {
  return (
    <article
      className={cn(
        'flex w-[min(15.5rem,calc(100vw-2.5rem))] shrink-0 flex-col rounded-xl bg-white/[0.95] p-4 shadow-md shadow-orange-950/15 ring-1 ring-white/25 backdrop-blur-sm sm:w-[17rem]',
        className
      )}
    >
      <ClientLogo
        logoSrc={client.logoSrc}
        logoAlt={client.logoAlt}
        fallbackMark={client.fallbackMark}
        darkLogoPlate={client.darkLogoPlate}
      />
      <h3 className="mt-3 text-base font-semibold tracking-tight text-stone-900">{client.name}</h3>
      <p className="mt-0.5 text-xs font-medium text-orange-700">{client.category}</p>
      <p className="mt-2 line-clamp-3 flex-1 text-xs leading-relaxed text-stone-600">{client.summary}</p>
      <a
        href={client.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 inline-flex min-h-[44px] items-center text-sm font-medium text-brand-primary transition-colors hover:text-fikiri-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/80 focus-visible:ring-offset-2 touch-manipulation"
      >
        Visit site
        <span className="sr-only"> ({client.name})</span>
        <span aria-hidden className="ml-1">
          →
        </span>
      </a>
    </article>
  )
}

export function ClientPartnerships() {
  const reduceMotion = useReducedMotion()
  const statusId = useId()
  const trackRef = useRef<HTMLDivElement>(null)
  const stickyPausedRef = useRef(false)
  const [paused, setPaused] = useState(false)

  const setStickyPaused = (next: boolean) => {
    stickyPausedRef.current = next
    setPaused(next)
  }

  const setTransientPaused = (next: boolean) => {
    if (stickyPausedRef.current) return
    setPaused(next)
  }

  useEffect(() => {
    const track = trackRef.current
    if (!track || reduceMotion) return
    track.style.animationPlayState = paused ? 'paused' : 'running'
  }, [paused, reduceMotion])

  return (
    <section
      className="relative overflow-hidden py-12 sm:py-14 lg:py-16"
      id="client-partnerships"
      aria-labelledby="client-partnerships-heading"
    >
      <style>{`
        @keyframes fikiri-partnerships-rtl {
          from { transform: translate3d(0, 0, 0); }
          to { transform: translate3d(-50%, 0, 0); }
        }
        .fikiri-partnerships-track {
          width: max-content;
          animation: fikiri-partnerships-rtl ${LOOP_SECONDS}s linear infinite;
          will-change: transform;
        }
        @media (prefers-reduced-motion: reduce) {
          .fikiri-partnerships-track {
            animation: none !important;
            transform: none !important;
          }
        }
      `}</style>

      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand-primary/40 to-transparent"
        aria-hidden
      />

      <Container className="relative">
        <Reveal direction="up">
          <Subheading dark>Client Partnerships</Subheading>
          <Heading as="h2" dark id="client-partnerships-heading" className="mt-2 max-w-3xl text-3xl sm:text-4xl md:text-5xl">
            Real client work across different industries.
          </Heading>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-white/80 sm:mt-4 sm:text-base">
            Fikiri starts with consulting and workflow discovery. From there, we help businesses
            plan, build, and support practical systems around their real operations — from
            automation and CRM to product workflows, cloud support, and custom tools.
          </p>
        </Reveal>
      </Container>

      <div className="relative mt-8 sm:mt-10">
        <div
          className="relative touch-pan-y"
          onMouseEnter={() => setTransientPaused(true)}
          onMouseLeave={() => setTransientPaused(false)}
          onPointerDown={() => setTransientPaused(true)}
          onPointerUp={() => setTransientPaused(false)}
          onPointerCancel={() => setTransientPaused(false)}
          onFocusCapture={() => setTransientPaused(true)}
          onBlurCapture={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setTransientPaused(false)
            }
          }}
        >
          <div
            className="overflow-hidden"
            role="region"
            aria-roledescription="carousel"
            aria-label="Client partnership cards"
            aria-describedby={statusId}
          >
            <p id={statusId} className="sr-only" aria-live="polite">
              Client partnerships scroll continuously from right to left. Pause by hovering, touching,
              or focusing the cards, or use the pause control. Use the list below for direct links.
            </p>

            {reduceMotion ? (
              <Container>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {clientPartnerships.map((client) => (
                    <PartnershipCard key={client.name} client={client} className="w-full max-w-full" />
                  ))}
                </div>
              </Container>
            ) : (
              <div
                ref={trackRef}
                className="fikiri-partnerships-track flex gap-4 px-4 sm:gap-5 sm:px-6"
              >
                {clientPartnerships.map((client) => (
                  <PartnershipCard key={`a-${client.name}`} client={client} />
                ))}
                <div className="flex gap-4 sm:gap-5" aria-hidden>
                  {clientPartnerships.map((client) => (
                    <PartnershipCard key={`b-${client.name}`} client={client} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Edge fades so the belt feels integrated with the wash */}
          {!reduceMotion && (
            <>
              <div
                className="pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-[#1c1510] to-transparent sm:w-16"
                aria-hidden
              />
              <div
                className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-[#1c1510] to-transparent sm:w-16"
                aria-hidden
              />
            </>
          )}
        </div>

        {!reduceMotion && (
          <div className="mt-4 flex justify-center sm:mt-5">
            <button
              type="button"
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full border border-white/20 bg-black/40 px-4 text-sm font-medium text-white backdrop-blur-sm touch-manipulation hover:bg-black/55"
              aria-pressed={paused}
              onClick={() => setStickyPaused(!stickyPausedRef.current)}
            >
              {paused ? 'Resume' : 'Pause'} carousel
            </button>
          </div>
        )}
      </div>

      <Container className="relative">
        <ul className="sr-only">
          {clientPartnerships.map((client) => (
            <li key={`sr-${client.name}`}>
              <a href={client.url} target="_blank" rel="noopener noreferrer">
                {client.name} — Visit site
              </a>
            </li>
          ))}
        </ul>

        <Reveal direction="scale" delay={0.08} className="mt-8 sm:mt-10">
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
