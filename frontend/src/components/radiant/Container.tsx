import { clsx } from 'clsx'

export function Container({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={clsx(
        className,
        'px-4 sm:px-6 lg:px-8',
        'pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))] sm:pl-[max(1.5rem,env(safe-area-inset-left))] sm:pr-[max(1.5rem,env(safe-area-inset-right))]'
      )}
    >
      <div className="mx-auto max-w-2xl lg:max-w-7xl 2xl:max-w-7xl 3xl:max-w-[1600px]">{children}</div>
    </div>
  )
}
