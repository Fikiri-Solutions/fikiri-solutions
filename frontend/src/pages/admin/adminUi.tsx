/**
 * Presentation-only admin UI primitives.
 * No fetching, auth, capabilities, eligibility, env, or global state.
 */
import type { ElementType, ReactNode } from 'react'

export type StatusTone = 'ok' | 'warn' | 'bad' | 'neutral' | 'unknown'

export type CanonicalChecklistStatus =
  | 'healthy'
  | 'attention'
  | 'blocked'
  | 'unknown'
  | 'not_applicable'
  | 'at_risk'

const TONE_CLASSES: Record<StatusTone, string> = {
  ok: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100',
  warn: 'bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100',
  bad: 'bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-100',
  neutral: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100',
  unknown: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
}

/** Map known status strings to badge tones without deriving business eligibility. */
export function toneForStatusLabel(status: string | undefined): StatusTone {
  switch ((status || '').toLowerCase()) {
    case 'healthy':
    case 'ok':
    case 'success':
    case 'active':
    case 'connected':
    case 'available':
      return 'ok'
    case 'attention':
    case 'warn':
    case 'warning':
    case 'expired':
    case 'refresh_failed':
    case 'past_due':
    case 'stale':
    case 'at_risk':
      return 'warn'
    case 'blocked':
    case 'bad':
    case 'failed':
    case 'failure':
    case 'denied':
    case 'revoked':
    case 'disconnected':
    case 'inactive':
      return 'bad'
    case 'not_applicable':
    case 'n/a':
    case 'disabled':
    case 'unavailable':
      return 'neutral'
    default:
      return 'unknown'
  }
}

export function StatusBadge({
  label,
  tone,
}: {
  label: string
  tone: StatusTone
}) {
  return (
    <span
      className={`inline-flex max-w-full items-center rounded-md px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  )
}

const PANEL_BASE =
  'scroll-mt-28 rounded-xl border border-zinc-200/90 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900'

export function AdminPanel({
  id,
  title,
  description,
  right,
  children,
  empty,
  className = '',
  headingAs: HeadingTag = 'h2',
}: {
  id?: string
  title: string
  description?: ReactNode
  right?: ReactNode
  children?: ReactNode
  empty?: boolean
  className?: string
  /** Caller chooses heading level for a valid document hierarchy. */
  headingAs?: ElementType
}) {
  return (
    <section id={id} className={`${PANEL_BASE} ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <HeadingTag className="text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            {title}
          </HeadingTag>
          {description ? (
            <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">{description}</div>
          ) : null}
        </div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>
      {empty ? (
        <p className="mt-3 text-sm text-zinc-500">No data available.</p>
      ) : children != null && children !== false ? (
        <div className="mt-4">{children}</div>
      ) : null}
    </section>
  )
}

export function AdminSubPanel({
  id,
  title,
  description,
  right,
  children,
  className = '',
  headingAs: HeadingTag = 'h3',
}: {
  id?: string
  title: string
  description?: ReactNode
  right?: ReactNode
  children?: ReactNode
  className?: string
  headingAs?: ElementType
}) {
  return (
    <div
      id={id}
      className={`scroll-mt-28 rounded-lg border border-zinc-100 bg-zinc-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-950/40 ${className}`.trim()}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <HeadingTag className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {title}
          </HeadingTag>
          {description ? (
            <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{description}</div>
          ) : null}
        </div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  )
}

export type MetricAvailability = 'ok' | 'disabled' | 'unavailable' | 'unknown' | 'empty'

export function MetricTile({
  label,
  value,
  hint,
  status,
  availability = 'ok',
}: {
  label: string
  /** Pass null/undefined for missing — never coerce to 0 here. */
  value?: ReactNode | null
  hint?: ReactNode
  status?: ReactNode
  availability?: MetricAvailability
}) {
  const isMissing = value === null || value === undefined || value === ''
  let display: ReactNode
  let displayHint = hint

  if (availability === 'disabled') {
    display = 'Disabled'
    displayHint = displayHint ?? 'Analytics disabled'
  } else if (availability === 'unavailable') {
    display = 'Unavailable'
  } else if (availability === 'unknown') {
    display = 'Unknown'
  } else if (availability === 'empty' || isMissing) {
    display = '—'
  } else {
    display = value
  }

  return (
    <div className="min-w-0 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {label}
        </p>
        {status}
      </div>
      <p className="mt-1 break-words text-lg font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
        {display}
      </p>
      {displayHint ? (
        <p className="mt-0.5 break-words text-xs text-zinc-500 dark:text-zinc-400">{displayHint}</p>
      ) : null}
    </div>
  )
}

export function FieldGrid({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <dl
      className={`grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 ${className}`.trim()}
    >
      {children}
    </dl>
  )
}

export function FieldItem({
  label,
  value,
  className = '',
}: {
  label: string
  value?: ReactNode | null
  className?: string
}) {
  return (
    <div className={`min-w-0 ${className}`.trim()}>
      <dt className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd className="mt-0.5 break-words text-zinc-900 dark:text-zinc-100">{value ?? '—'}</dd>
    </div>
  )
}

export function checklistStatusLabel(status: string): string {
  switch (status) {
    case 'healthy':
      return 'Healthy'
    case 'attention':
      return 'Attention'
    case 'blocked':
      return 'Blocked'
    case 'not_applicable':
      return 'N/A'
    case 'unknown':
      return 'Unknown'
    case 'at_risk':
      return 'At risk'
    default:
      return String(status)
  }
}

export function checklistTone(status: string): StatusTone {
  switch (status) {
    case 'healthy':
      return 'ok'
    case 'attention':
    case 'at_risk':
      return 'warn'
    case 'blocked':
      return 'bad'
    case 'not_applicable':
      return 'neutral'
    default:
      return 'unknown'
  }
}
