import { motion, useReducedMotion } from 'framer-motion'
import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'

export type RevealDirection = 'up' | 'down' | 'left' | 'right' | 'scale'

type RevealProps = {
  children: ReactNode
  className?: string
  /** Stagger delay in seconds */
  delay?: number
  /**
   * Reveal direction. Defaults to upward lift.
   * Legacy `distance` still applies to up/down/left/right travel.
   * On narrow viewports reveals are skipped (see component body).
   */
  direction?: RevealDirection
  /** Travel distance in px for directional reveals (default 32) */
  distance?: number
  /** Fire only once when entering viewport (default true) */
  once?: boolean
  /** Viewport amount 0–1 before triggering (default 0.25) */
  amount?: number
}

const EASE = [0.22, 1, 0.36, 1] as const
const MOBILE_MQ = '(max-width: 639px)'

function readNarrowViewport(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  try {
    return window.matchMedia(MOBILE_MQ).matches
  } catch {
    return false
  }
}

function useIsNarrowViewport() {
  // Sync on first paint so mobile never flashes opacity:0 then "never reveals".
  const [narrow, setNarrow] = useState(readNarrowViewport)
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(MOBILE_MQ)
    const sync = () => setNarrow(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])
  return narrow
}

function initialFor(direction: RevealDirection, distance: number) {
  switch (direction) {
    case 'down':
      return { opacity: 0, y: -distance }
    case 'left':
      return { opacity: 0, x: -Math.min(distance + 8, 48) }
    case 'right':
      return { opacity: 0, x: Math.min(distance + 8, 48) }
    case 'scale':
      return { opacity: 0, y: 16, scale: 0.98 }
    case 'up':
    default:
      return { opacity: 0, y: distance }
  }
}

/**
 * Scroll-triggered marketing reveal. Respects prefers-reduced-motion.
 * On narrow phones, skip hide-until-in-view — IntersectionObserver + opacity:0
 * is a common “missing content” failure on iOS Chrome / in-app browsers.
 * Prefer this (or MarketingReveal) over one-off motion wrappers on public pages.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  direction = 'up',
  distance = 32,
  once = true,
  amount = 0.25,
}: RevealProps) {
  const reduceMotion = useReducedMotion()
  const narrow = useIsNarrowViewport()

  // Visibility first on phones and reduced-motion — desktop keeps the reveal.
  if (reduceMotion || narrow) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={clsx(className)}
      initial={initialFor(direction, distance)}
      whileInView={{ opacity: 1, x: 0, y: 0, scale: 1 }}
      viewport={{ once, amount, margin: '0px 0px -6% 0px' }}
      transition={{ duration: 0.6, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  )
}

/** Alias matching the marketing motion brief */
export const MarketingReveal = Reveal
