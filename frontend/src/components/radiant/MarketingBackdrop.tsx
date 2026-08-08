import { clsx } from 'clsx'
import { AnimatedBackground } from './AnimatedBackground'

/**
 * Full-page charcoal/amber marketing wash shared by public radiant pages.
 * Fixed so the orbital motion stays visible while scrolling.
 */
export function MarketingBackdrop({
  className,
  intensity = 'strong',
}: {
  className?: string
  intensity?: 'subtle' | 'strong'
}) {
  return (
    <div
      className={clsx(
        'pointer-events-none fixed inset-0 overflow-hidden',
        className
      )}
      aria-hidden
    >
      <div className="absolute inset-0 bg-gradient-to-b from-[#140f0c] via-[#1c1510] to-[#241910]" />
      <div className="absolute inset-0 opacity-90">
        <div className="absolute -left-24 top-10 h-48 w-48 rounded-full bg-brand-primary/22 blur-3xl sm:h-72 sm:w-72 sm:bg-brand-primary/30" />
        <div className="absolute right-0 top-24 h-56 w-56 rounded-full bg-orange-500/14 blur-3xl sm:h-96 sm:w-96 sm:bg-orange-500/20" />
        <div className="absolute bottom-0 left-1/3 h-40 w-40 rounded-full bg-amber-700/14 blur-3xl sm:h-64 sm:w-64 sm:bg-amber-700/20" />
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='56' height='56' viewBox='0 0 56 56' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fb923c' fill-opacity='0.12'%3E%3Ccircle cx='2' cy='2' r='1.2'/%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(255,107,53,0.18),_transparent_55%)]" />
      </div>
      <AnimatedBackground intensity={intensity} />
      {/* Soft center scrim so open-air copy stays readable over bright orbs */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(20,15,12,0.35)_0%,_transparent_70%)]" />
      <div className="absolute inset-0 bg-black/15" />
    </div>
  )
}
