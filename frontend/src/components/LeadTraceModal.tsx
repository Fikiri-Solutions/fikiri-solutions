import React, { useEffect, useMemo, useRef, useState } from 'react'
import { GitBranch, X } from 'lucide-react'
import { apiClient, type LeadCrmEvent, type LeadData } from '../services/apiClient'
import { useToast } from './Toast'
import {
  flattenCorrelationTraceForTimeline,
  orderedUniqueCorrelationIds
} from '../utils/correlationTrace'

type Props = {
  lead: LeadData | null
  open: boolean
  onClose: () => void
}

function messageFromApiError(err: unknown, fallback: string): string {
  if (!err || typeof err !== 'object' || !('response' in err)) return fallback
  const data = (err as { response?: { data?: Record<string, unknown> } }).response
    ?.data
  if (!data || typeof data !== 'object') return fallback
  const e = data.error
  if (typeof e === 'string' && e.trim()) return e
  const m = data.message
  if (typeof m === 'string' && m.trim()) return m
  const c = data.code
  if (typeof c === 'string' && c.trim()) return c
  return fallback
}

export const LeadTraceModal: React.FC<Props> = ({ lead, open, onClose }) => {
  const { addToast } = useToast()
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const [eventsLoading, setEventsLoading] = useState(false)
  const [eventsError, setEventsError] = useState<string | null>(null)
  const [crmEvents, setCrmEvents] = useState<LeadCrmEvent[]>([])
  const [correlationInput, setCorrelationInput] = useState('')
  const [traceLoading, setTraceLoading] = useState(false)
  const [trace, setTrace] = useState<Awaited<
    ReturnType<typeof apiClient.getCorrelationTrace>
  > | null>(null)

  const idChips = useMemo(
    () => orderedUniqueCorrelationIds(crmEvents),
    [crmEvents]
  )

  useEffect(() => {
    if (!open || !lead) return
    let cancelled = false
    setEventsLoading(true)
    setEventsError(null)
    setCrmEvents([])
    setTrace(null)
    setCorrelationInput('')
    void apiClient
      .getLeadCrmEvents(lead.id, { limit: 100 })
      .then((data) => {
        if (cancelled) return
        setCrmEvents(data.events)
        const ids = orderedUniqueCorrelationIds(data.events)
        setCorrelationInput(ids[0] ?? '')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setEventsError(messageFromApiError(err, 'Could not load CRM events'))
      })
      .finally(() => {
        if (!cancelled) setEventsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, lead?.id])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  if (!open || !lead) return null

  const timeline = flattenCorrelationTraceForTimeline(trace)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-600/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lead-trace-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-gray-200 bg-white p-5 shadow-lg dark:border-gray-700 dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 shrink-0 text-brand-primary" />
            <div>
              <h3
                id="lead-trace-title"
                className="text-lg font-semibold text-brand-text dark:text-white"
              >
                View trace
              </h3>
              <p className="text-sm text-brand-text/70 dark:text-gray-400">
                {lead.name} · {lead.email}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-brand-text/60 hover:bg-brand-text/10 dark:text-gray-400 dark:hover:bg-gray-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4 space-y-3 text-sm text-brand-text dark:text-gray-200">
          {eventsLoading ? (
            <p className="text-xs text-brand-text/60 dark:text-gray-400">
              Loading CRM events…
            </p>
          ) : eventsError ? (
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {eventsError} You can still paste a correlation ID below if you
              have one.
            </p>
          ) : idChips.length === 0 ? (
            <p className="text-xs text-brand-text/60 dark:text-gray-400">
              {crmEvents.length === 0
                ? 'No CRM events recorded for this lead yet.'
                : 'No correlation IDs on CRM events yet. Paste an ID from an API response or Automations debug if you have one.'}
            </p>
          ) : null}

          {idChips.length > 0 ? (
            <div>
              <p className="text-[11px] font-medium text-brand-text/60 dark:text-gray-400">
                From CRM events (newest first)
              </p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {idChips.map((id) => (
                  <button
                    key={id}
                    type="button"
                    className="max-w-full truncate rounded-md border border-brand-text/15 bg-brand-text/5 px-2 py-0.5 font-mono text-[10px] text-brand-text hover:bg-brand-text/10 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300"
                    title={id}
                    onClick={() => setCorrelationInput(id)}
                  >
                    {id.length > 36 ? `${id.slice(0, 8)}…${id.slice(-6)}` : id}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <label className="block text-xs font-medium text-brand-text/70 dark:text-gray-400">
            Correlation ID
            <input
              type="text"
              className="mt-1 w-full rounded-lg border border-brand-text/20 bg-white px-3 py-2 font-mono text-xs text-brand-text focus:border-brand-accent focus:ring-brand-accent dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
              placeholder="From CRM events or paste"
              value={correlationInput}
              onChange={(e) => setCorrelationInput(e.target.value)}
            />
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!correlationInput.trim()}
              className="rounded-md border border-brand-text/20 px-3 py-1.5 text-xs font-medium text-brand-text hover:bg-brand-text/5 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(correlationInput.trim())
                  addToast({ type: 'success', title: 'Copied correlation ID' })
                } catch {
                  addToast({
                    type: 'error',
                    title: 'Copy failed',
                    message: 'Clipboard access was denied. Copy the ID manually.'
                  })
                }
              }}
            >
              Copy ID
            </button>
            <button
              type="button"
              disabled={traceLoading || !correlationInput.trim()}
              className="rounded-md border border-brand-primary/40 bg-brand-primary/10 px-3 py-1.5 text-xs font-medium text-brand-primary disabled:opacity-50"
              onClick={async () => {
                const id = correlationInput.trim()
                if (!id) return
                setTraceLoading(true)
                setTrace(null)
                try {
                  const t = await apiClient.getCorrelationTrace(id)
                  setTrace(t)
                  if (!t) {
                    addToast({
                      type: 'warning',
                      title: 'No trace data',
                      message: 'The server returned an empty trace.'
                    })
                  }
                } catch (e: unknown) {
                  addToast({
                    type: 'error',
                    title: 'Trace failed',
                    message: messageFromApiError(e, 'Trace request failed')
                  })
                } finally {
                  setTraceLoading(false)
                }
              }}
            >
              {traceLoading ? 'Loading…' : 'Load stitched trace'}
            </button>
          </div>

          {timeline.length > 0 ? (
            <div className="rounded-md border border-brand-text/10 dark:border-gray-600">
              <p className="border-b border-brand-text/10 px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide text-brand-text/60 dark:border-gray-600 dark:text-gray-400">
                Timeline
              </p>
              <ul className="max-h-48 overflow-auto text-xs">
                {timeline.slice(0, 80).map((row, i) => (
                  <li
                    key={`${row.at}-${row.title}-${i}`}
                    className="border-b border-brand-text/5 px-2 py-1.5 last:border-0 dark:border-gray-700/50"
                  >
                    <span className="mr-2 rounded bg-brand-text/10 px-1.5 py-0.5 font-medium text-[10px] text-brand-text dark:bg-gray-700 dark:text-gray-200">
                      {row.domain}
                    </span>
                    <span className="font-medium text-brand-text dark:text-gray-100">
                      {row.title}
                    </span>
                    {row.subtitle ? (
                      <span className="text-brand-text/60 dark:text-gray-400">
                        {' '}
                        · {row.subtitle}
                      </span>
                    ) : null}
                    {row.at ? (
                      <span className="block text-[10px] text-brand-text/50 dark:text-gray-500">
                        {row.at}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : trace ? (
            <p className="text-xs text-brand-text/60 dark:text-gray-400">
              No timeline rows parsed; see raw JSON below.
            </p>
          ) : null}

          {trace ? (
            <details className="rounded-md border border-dashed border-brand-text/20 dark:border-gray-600">
              <summary className="cursor-pointer px-2 py-1.5 text-xs font-medium text-brand-text dark:text-gray-200">
                Raw JSON
              </summary>
              <pre className="max-h-56 overflow-auto border-t border-brand-text/10 p-2 text-[10px] leading-snug text-brand-text dark:border-gray-600 dark:text-gray-200">
                {JSON.stringify(trace, null, 2)}
              </pre>
            </details>
          ) : null}
        </div>

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-brand-text/20 px-4 py-2 text-sm font-medium text-brand-text hover:bg-brand-text/5 dark:border-gray-600 dark:text-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
