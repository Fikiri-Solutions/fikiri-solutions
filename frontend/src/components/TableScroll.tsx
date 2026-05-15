import { clsx } from 'clsx'

type TableScrollProps = {
  children: React.ReactNode
  className?: string
  /** wide = pricing/compare (42rem), medium = billing/crm (40rem), full = min-w-full only */
  size?: 'wide' | 'medium' | 'full'
  label?: string
}

/**
 * Horizontal scroll wrapper for data tables on narrow viewports.
 * Prevents column headers and cells from breaking letter-by-letter when squeezed.
 */
export function TableScroll({
  children,
  className,
  size = 'wide',
  label = 'Scroll horizontally to see all columns',
}: TableScrollProps) {
  return (
    <div
      className={clsx(
        'table-scroll',
        size === 'wide' && 'table-scroll--wide',
        size === 'medium' && 'table-scroll--medium',
        size === 'full' && 'table-scroll--full',
        className
      )}
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      {children}
    </div>
  )
}
