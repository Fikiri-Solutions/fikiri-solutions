import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { clsx } from 'clsx'
import { publicMedia } from '@/lib/publicMedia'

/** Matches MarketingBackdrop top wash — fade destination, not a new black. */
const PAGE_BG = '#140f0c'

export const HERO_SEEN_SESSION_KEY = 'fikiri-hero-seen'

const EASE = [0.22, 1, 0.36, 1] as const

type HeroEntranceValue = {
  entered: boolean
  instant: boolean
}

const HeroEntranceContext = createContext<HeroEntranceValue>({
  entered: true,
  instant: true,
})

export function useHeroEntrance() {
  return useContext(HeroEntranceContext)
}

function readHeroSeen(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return sessionStorage.getItem(HERO_SEEN_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

function prefersReducedMotionSync(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

/** Narrow phones: skip long staged delays so the first viewport is not an empty charcoal gap. */
function isNarrowViewportSync(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.matchMedia('(max-width: 767px)').matches
  } catch {
    return false
  }
}

function markHeroSeen() {
  try {
    sessionStorage.setItem(HERO_SEEN_SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
}

type FikiriHeroVisualProps = {
  className?: string
  children?: ReactNode
}

/**
 * Continuous hero field + mount/in-view entrance motion.
 * Static composition is the approved resting state — motion only transitions into it.
 */
export function FikiriHeroVisual({ className, children }: FikiriHeroVisualProps) {
  const sectionRef = useRef<HTMLElement | null>(null)
  const reduceMotion = useReducedMotion()
  const [seenThisSession] = useState(readHeroSeen)
  const [prefersReduced] = useState(prefersReducedMotionSync)
  const [narrowViewport] = useState(isNarrowViewportSync)
  // Mobile: enter immediately — long staged delays leave a blank first paint that looks "broken".
  const instant =
    Boolean(reduceMotion) || prefersReduced || seenThisSession || narrowViewport
  const [entered, setEntered] = useState(instant)

  useEffect(() => {
    if (instant) {
      setEntered(true)
      if (narrowViewport && !seenThisSession) markHeroSeen()
      return
    }

    const node = sectionRef.current
    if (!node || typeof IntersectionObserver === 'undefined') {
      setEntered(true)
      markHeroSeen()
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return
        setEntered(true)
        markHeroSeen()
        observer.disconnect()
      },
      // Low threshold so tall hero sections still trigger on short mobile viewports.
      { threshold: 0.05 }
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [instant, narrowViewport, seenThisSession])

  const treeTransition = instant
    ? { duration: 0.2, ease: EASE }
    : { duration: 1.15, ease: EASE, delay: 0.3 }

  return (
    <HeroEntranceContext.Provider value={{ entered, instant }}>
      <section
        ref={sectionRef}
        className={clsx('relative w-full overflow-x-hidden', className)}
        aria-label="Fikiri Solutions brand hero"
        data-hero-entered={entered ? 'true' : 'false'}
        data-hero-instant={instant ? 'true' : 'false'}
        style={{ backgroundColor: PAGE_BG }}
      >
        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
          {/* Outer keeps absolute placement; inner motion only opacity/scale/y */}
          <div className="absolute left-1/2 top-0 h-[min(78vw,420px)] w-auto max-w-none -translate-x-1/2 sm:h-[min(58vw,620px)] md:h-[min(52vw,680px)] lg:h-[min(48vw,720px)]">
            <motion.div
              className="h-full w-auto origin-center"
              initial={false}
              animate={
                entered
                  ? { opacity: 1, scale: 1, y: 0 }
                  : { opacity: 0, scale: 0.985, y: 8 }
              }
              transition={treeTransition}
            >
              <picture>
                <source media="(max-width: 767px)" srcSet={publicMedia.landing.hero.mobile} />
                <img
                  src={publicMedia.landing.hero.desktop}
                  alt=""
                  width={1024}
                  height={576}
                  decoding="async"
                  className="h-full w-auto max-w-none object-contain object-top"
                  style={
                    narrowViewport
                      ? {
                          // Soft bottom fade only — heavy dual masks made the baobab a ghost on phones.
                          WebkitMaskImage:
                            'linear-gradient(to bottom, #000 0%, #000 58%, rgba(0,0,0,0.75) 78%, transparent 100%)',
                          maskImage:
                            'linear-gradient(to bottom, #000 0%, #000 58%, rgba(0,0,0,0.75) 78%, transparent 100%)',
                        }
                      : {
                          WebkitMaskImage: [
                            'radial-gradient(ellipse 72% 68% at 50% 32%, #000 28%, rgba(0,0,0,0.92) 48%, rgba(0,0,0,0.55) 68%, transparent 86%)',
                            'linear-gradient(to bottom, #000 0%, #000 48%, rgba(0,0,0,0.55) 72%, transparent 100%)',
                          ].join(', '),
                          maskImage: [
                            'radial-gradient(ellipse 72% 68% at 50% 32%, #000 28%, rgba(0,0,0,0.92) 48%, rgba(0,0,0,0.55) 68%, transparent 86%)',
                            'linear-gradient(to bottom, #000 0%, #000 48%, rgba(0,0,0,0.55) 72%, transparent 100%)',
                          ].join(', '),
                          WebkitMaskComposite: 'source-in',
                          maskComposite: 'intersect',
                        }
                  }
                />
              </picture>
            </motion.div>
          </div>

          {/* Desktop: stronger edge wash. Mobile: lighter so canopy lights + sunset read. */}
          <div
            className="absolute inset-0 hidden sm:block"
            style={{
              background: `
                linear-gradient(to right, ${PAGE_BG} 0%, transparent 16%, transparent 84%, ${PAGE_BG} 100%),
                linear-gradient(to bottom, ${PAGE_BG} 0%, transparent 10%, transparent 42%, ${PAGE_BG} 88%),
                radial-gradient(ellipse 95% 80% at 50% 30%, transparent 35%, ${PAGE_BG} 92%)
              `,
            }}
          />
          <div
            className="absolute inset-0 sm:hidden"
            style={{
              background: `
                linear-gradient(to right, ${PAGE_BG} 0%, transparent 8%, transparent 92%, ${PAGE_BG} 100%),
                linear-gradient(to bottom, ${PAGE_BG}cc 0%, transparent 14%, transparent 55%, ${PAGE_BG} 96%),
                radial-gradient(ellipse 110% 90% at 50% 28%, transparent 42%, ${PAGE_BG}99 100%)
              `,
            }}
          />

          <div
            className="absolute inset-x-0 bottom-0 h-[28%] sm:h-[42%]"
            style={{
              background: `linear-gradient(to top, ${PAGE_BG} 0%, ${PAGE_BG} 18%, ${PAGE_BG}cc 45%, transparent 100%)`,
            }}
          />
        </div>

        <div className="relative z-10">{children}</div>
      </section>
    </HeroEntranceContext.Provider>
  )
}

function RevealItem({
  children,
  className,
  delay,
  scaleFrom,
  yFrom = 6,
  duration = 0.55,
}: {
  children: ReactNode
  className?: string
  delay: number
  scaleFrom?: number
  yFrom?: number
  duration?: number
}) {
  const { entered, instant } = useHeroEntrance()
  const transition = instant
    ? { duration: 0.2, ease: EASE }
    : { duration, ease: EASE, delay }

  return (
    <motion.div
      className={className}
      initial={false}
      animate={
        entered
          ? { opacity: 1, y: 0, scale: 1 }
          : { opacity: 0, y: yFrom, scale: scaleFrom ?? 1 }
      }
      transition={transition}
    >
      {children}
    </motion.div>
  )
}

export function FikiriHeroBrandBlock() {
  const { entered, instant } = useHeroEntrance()

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-4 text-center">
      <RevealItem delay={2.2} scaleFrom={0.97} yFrom={6} duration={0.65}>
        <div>
          <p className="font-serif text-2xl font-bold tracking-[0.08em] text-white drop-shadow-[0_2px_18px_rgba(20,15,12,0.85)] sm:text-3xl md:text-4xl">
            FIKIRI
          </p>
          <p className="mt-1 text-[0.65rem] font-semibold tracking-[0.34em] text-orange-300 sm:text-xs md:text-sm">
            SOLUTIONS
          </p>
        </div>
      </RevealItem>

      <ul className="mt-8 hidden w-full max-w-5xl list-none grid-cols-3 gap-6 text-left lg:grid">
        <li className="min-w-0">
          <RevealItem delay={1.1}>
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-orange-300">
              Smart Communication
            </p>
            <p className="mt-1 text-xs leading-snug text-white/70">
              Respond faster. Never miss what matters.
            </p>
          </RevealItem>
        </li>
        <li className="min-w-0 text-center">
          <RevealItem delay={1.45}>
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-orange-300">
              Customer Relationships
            </p>
            <p className="mt-1 text-xs leading-snug text-white/70">
              Know your customers. Strengthen every relationship.
            </p>
          </RevealItem>
        </li>
        <li className="min-w-0 text-right">
          <RevealItem delay={1.8}>
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-orange-300">
              Intelligent Automation
            </p>
            <p className="mt-1 text-xs leading-snug text-white/70">
              Automate the friction. Focus on growth.
            </p>
          </RevealItem>
        </li>
      </ul>

      <RevealItem delay={2.7} yFrom={8} className="mt-6 sm:mt-8" duration={0.6}>
        <h2 className="max-w-3xl font-serif text-xl font-medium leading-snug text-[#f5efe6] sm:text-2xl md:text-3xl">
          Intelligent systems for the way
          <br className="hidden sm:block" />{' '}
          your business{' '}
          <em className="font-serif italic text-[#d96b28]">actually works.</em>
        </h2>
      </RevealItem>

      <span
        className="sr-only"
        data-hero-brand-entered={entered ? 'true' : 'false'}
        data-hero-instant={instant ? 'true' : 'false'}
      />
    </div>
  )
}

/** Subtle Sector Fit settle — never blocks interaction */
export function FikiriHeroSectorSettle({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  const { entered, instant } = useHeroEntrance()
  return (
    <motion.div
      className={className}
      initial={false}
      animate={entered ? { opacity: 1, y: 0 } : { opacity: 0.92, y: 10 }}
      transition={
        instant
          ? { duration: 0.2, ease: EASE }
          : { duration: 0.55, ease: EASE, delay: 3.1 }
      }
    >
      {children}
    </motion.div>
  )
}
