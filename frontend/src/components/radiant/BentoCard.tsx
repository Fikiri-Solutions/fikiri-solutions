import { clsx } from 'clsx'
import { motion } from 'framer-motion'
import { Subheading } from './Text'

export function BentoCard({
  dark = false,
  className = '',
  eyebrow,
  title,
  description,
  graphic,
  fade = [],
}: {
  dark?: boolean
  className?: string
  eyebrow: React.ReactNode
  title: React.ReactNode
  description: React.ReactNode
  graphic: React.ReactNode
  fade?: ('top' | 'bottom')[]
}) {
  return (
    <motion.div
      initial="idle"
      whileHover="active"
      variants={{ idle: {}, active: {} }}
      data-dark={dark ? 'true' : undefined}
      className={clsx(
        className,
        'group relative flex flex-col overflow-hidden rounded-2xl',
        'bg-card shadow-sm ring-1 ring-border',
        dark && 'bg-gray-800 ring-white/15'
      )}
    >
      <div className="relative h-80 shrink-0">
        {graphic}
        {fade.includes('top') && (
          <div
            className={clsx(
              'absolute inset-0 bg-gradient-to-b from-card to-transparent to-50%',
              dark && 'from-gray-800'
            )}
          />
        )}
        {fade.includes('bottom') && (
          <div
            className={clsx(
              'absolute inset-0 bg-gradient-to-t from-card to-transparent to-50%',
              dark && 'from-gray-800'
            )}
          />
        )}
      </div>
      <div className="relative p-10">
        <Subheading as="h3" dark={dark}>
          {eyebrow}
        </Subheading>
        <p
          className={clsx(
            'mt-1 text-2xl font-medium tracking-tight',
            dark ? 'text-white' : 'text-foreground'
          )}
        >
          {title}
        </p>
        <p
          className={clsx(
            'mt-2 max-w-[600px] text-sm text-muted-foreground',
            dark && 'text-gray-400'
          )}
        >
          {description}
        </p>
      </div>
    </motion.div>
  )
}
