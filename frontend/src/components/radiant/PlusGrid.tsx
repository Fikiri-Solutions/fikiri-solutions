import { clsx } from 'clsx'

export function PlusGrid({
  className = '',
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return <div className={className}>{children}</div>
}

export function PlusGridRow({
  className = '',
  children,
  dense = false,
}: {
  className?: string
  children: React.ReactNode
  /** Tighter vertical padding for premium headers */
  dense?: boolean
}) {
  return (
    <div
      className={clsx(
        className,
        'relative isolate group/row',
        dense ? 'py-2' : 'pt-6 last:pb-6'
      )}
    >
      {!dense && (
        <div
          aria-hidden="true"
          className="absolute inset-y-0 left-1/2 -z-10 w-screen -translate-x-1/2"
        >
          <div className="absolute inset-x-0 top-0 border-t border-border" />
          <div className="absolute inset-x-0 top-2 border-t border-border" />
          <div className="absolute inset-x-0 bottom-0 hidden border-b border-border last:block" />
          <div className="absolute inset-x-0 bottom-2 hidden border-b border-border last:block" />
        </div>
      )}
      {children}
    </div>
  )
}

export function PlusGridItem({
  className = '',
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return <div className={clsx(className, 'relative')}>{children}</div>
}
