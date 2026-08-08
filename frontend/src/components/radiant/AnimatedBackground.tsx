import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { clsx } from 'clsx'

/**
 * Ambient full-page motion in Fikiri orange/charcoal tones.
 * Soft orbital rings + drifting orbs — motion is intentionally readable.
 * On narrow viewports, keep static wash (blur drift is expensive on weak GPUs).
 */
export function AnimatedBackground({
  intensity = 'strong',
}: {
  intensity?: 'subtle' | 'strong'
}) {
  const reduceMotion = useReducedMotion()
  const [allowMobileDrift, setAllowMobileDrift] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    const sync = () => setAllowMobileDrift(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])
  const drift = !reduceMotion && allowMobileDrift
  const strong = intensity === 'strong'

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      {/* Soft brand orbs */}
      <motion.div
        className={clsx(
          'absolute -left-16 top-24 rounded-full blur-3xl',
          // Smaller / quieter on phones; full presence from md up
          strong
            ? 'h-56 w-56 bg-brand-primary/28 sm:h-72 sm:w-72 sm:bg-brand-primary/35 md:h-[22rem] md:w-[22rem] md:bg-brand-primary/40'
            : 'h-48 w-48 bg-brand-primary/18 sm:h-64 sm:w-64 sm:bg-brand-primary/22 md:h-80 md:w-80 md:bg-brand-primary/25'
        )}
        animate={
          drift
            ? {
                x: strong ? [0, 56, -20, 0] : [0, 36, 0],
                y: strong ? [0, 40, -16, 0] : [0, 24, 0],
                scale: strong ? [1, 1.22, 0.96, 1] : [1, 1.12, 1],
              }
            : undefined
        }
        transition={{
          duration: strong ? 8 : 12,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      <motion.div
        className={clsx(
          'absolute -right-20 top-32 rounded-full blur-3xl',
          strong
            ? 'h-64 w-64 bg-orange-400/20 sm:h-80 sm:w-80 sm:bg-orange-400/25 md:h-[32rem] md:w-[32rem] md:bg-orange-400/30'
            : 'h-56 w-56 bg-orange-400/14 sm:h-72 sm:w-72 sm:bg-orange-400/18 md:h-[28rem] md:w-[28rem] md:bg-orange-400/20'
        )}
        animate={
          drift
            ? {
                x: strong ? [0, -48, 24, 0] : [0, -28, 0],
                y: strong ? [0, 56, -24, 0] : [0, 40, 0],
                scale: strong ? [1.1, 0.95, 1.18, 1.1] : [1.08, 1, 1.08],
              }
            : undefined
        }
        transition={{
          duration: strong ? 9.5 : 14,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      <motion.div
        className={clsx(
          'absolute bottom-8 left-1/3 rounded-full blur-3xl',
          strong
            ? 'h-48 w-48 bg-amber-500/16 sm:h-64 sm:w-64 sm:bg-amber-500/20 md:h-80 md:w-80 md:bg-amber-500/25'
            : 'h-40 w-40 bg-amber-600/10 sm:h-56 sm:w-56 sm:bg-amber-600/12 md:h-72 md:w-72 md:bg-amber-600/15'
        )}
        animate={
          drift
            ? {
                x: strong ? [0, 36, -28, 0] : [0, 20, 0],
                y: strong ? [0, -48, 20, 0] : [0, -30, 0],
                scale: strong ? [1, 1.2, 0.92, 1] : [1, 1.15, 1],
              }
            : undefined
        }
        transition={{
          duration: strong ? 7.5 : 11,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Orbital rings — visible from md up so motion reads on tablet+ */}
      <div
        className={clsx(
          'absolute right-[-10%] top-[8%] hidden overflow-hidden md:block',
          strong
            ? 'h-[420px] w-[420px] lg:right-[2%] lg:top-[4%] lg:h-[520px] lg:w-[520px]'
            : 'h-[380px] w-[380px] lg:right-[0%] lg:top-[6%] lg:h-[460px] lg:w-[460px]'
        )}
      >
        <motion.div
          className="absolute inset-0 rounded-full border border-brand-primary/40"
          animate={drift ? { rotate: 360 } : undefined}
          transition={{ duration: strong ? 28 : 50, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute inset-[14%] rounded-full border border-dashed border-orange-400/45"
          animate={drift ? { rotate: -360 } : undefined}
          transition={{ duration: strong ? 38 : 70, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute inset-[30%] rounded-full border border-brand-primary/35"
          animate={drift ? { rotate: 360 } : undefined}
          transition={{ duration: strong ? 22 : 38, repeat: Infinity, ease: 'linear' }}
        />
        {drift && (
          <>
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: 360 }}
              transition={{ duration: strong ? 10 : 18, repeat: Infinity, ease: 'linear' }}
            >
              <span className="absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 rounded-full bg-brand-primary shadow-[0_0_22px_rgba(255,107,53,0.9)]" />
            </motion.div>
            <motion.div
              className="absolute inset-[14%]"
              animate={{ rotate: -360 }}
              transition={{ duration: strong ? 14 : 26, repeat: Infinity, ease: 'linear' }}
            >
              <span className="absolute bottom-0 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-orange-400 shadow-[0_0_16px_rgba(251,146,60,0.85)]" />
            </motion.div>
            <motion.div
              className="absolute inset-[30%]"
              animate={{ rotate: 360 }}
              transition={{ duration: strong ? 8 : 14, repeat: Infinity, ease: 'linear' }}
            >
              <span className="absolute left-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-amber-300 shadow-[0_0_12px_rgba(252,211,77,0.8)]" />
            </motion.div>
          </>
        )}
      </div>

      {/* Second quieter orbit bottom-left for full-page presence */}
      {strong && (
        <div className="absolute bottom-[-8%] left-[-6%] hidden h-[280px] w-[280px] overflow-hidden opacity-70 lg:block">
          <motion.div
            className="absolute inset-0 rounded-full border border-orange-500/25"
            animate={drift ? { rotate: -360 } : undefined}
            transition={{ duration: 42, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="absolute inset-[22%] rounded-full border border-dashed border-brand-primary/20"
            animate={drift ? { rotate: 360 } : undefined}
            transition={{ duration: 56, repeat: Infinity, ease: 'linear' }}
          />
          {drift && (
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: -360 }}
              transition={{ duration: 16, repeat: Infinity, ease: 'linear' }}
            >
              <span className="absolute right-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-orange-300/90 shadow-[0_0_14px_rgba(253,186,116,0.75)]" />
            </motion.div>
          )}
        </div>
      )}

      {/* Dot grid texture */}
      <div
        className="absolute inset-0 opacity-[0.5]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='56' height='56' viewBox='0 0 56 56' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fb923c' fill-opacity='0.16'%3E%3Ccircle cx='2' cy='2' r='1.2'/%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />
    </div>
  )
}
