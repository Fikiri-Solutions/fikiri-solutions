import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { GitBranch, Loader2, Copy, ArrowLeft } from 'lucide-react'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { FIKIRI_LAST_AUTOMATION_CORRELATION_KEY } from '../constants/correlationDebug'
import {
  flattenCorrelationTraceForTimeline,
  getTraceRowQuickLink
} from '../utils/correlationTrace'

type TracePayload = Awaited<ReturnType<typeof apiClient.getCorrelationTrace>>

function formatTraceApiError(err: unknown): { title: string; detail: string } {
  if (err && typeof err === 'object' && 'response' in err) {
    const res = (err as { response?: { status?: number; data?: { error?: string; code?: string } } })
      .response
    const code = res?.data?.code
    const msg = res?.data?.error || 'Request failed'
    const st = res?.status
    if (code === 'TRACE_DISABLED' || (st === 404 && code !== 'INVALID_CORRELATION_ID')) {
      return {
        title: 'Correlation trace unavailable',
        detail:
          'The server disabled this endpoint (e.g. FIKIRI_CORRELATION_TRACE) or returned 404.'
      }
    }
    if (code === 'AUTHENTICATION_REQUIRED' || st === 401) {
      return { title: 'Authentication required', detail: 'Sign in again if your session expired.' }
    }
    if (code === 'INVALID_CORRELATION_ID' || st === 400) {
      return { title: 'Invalid correlation ID', detail: msg }
    }
    return { title: 'Could not load trace', detail: msg }
  }
  return { title: 'Could not load trace', detail: 'Network or unexpected error.' }
}

export const CorrelationDebugPage: React.FC = () => {
  const { addToast } = useToast()
  const [searchParams] = useSearchParams()
  const [correlationInput, setCorrelationInput] = useState('')
  const [trace, setTrace] = useState<TracePayload>(null)
  const [loadError, setLoadError] = useState<{ title: string; detail: string } | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const q = searchParams.get('id')?.trim()
    if (q) setCorrelationInput(q)
  }, [searchParams])

  const lastPresetId =
    typeof sessionStorage !== 'undefined'
      ? sessionStorage.getItem(FIKIRI_LAST_AUTOMATION_CORRELATION_KEY)?.trim() || null
      : null

  const timeline = useMemo(() => flattenCorrelationTraceForTimeline(trace), [trace])

  const loadTrace = useCallback(
    async (id: string) => {
      const trimmed = id.trim()
      if (!trimmed) return
      setLoading(true)
      setLoadError(null)
      setTrace(null)
      try {
        const t = await apiClient.getCorrelationTrace(trimmed)
        setTrace(t)
        if (!t) {
          setLoadError({
            title: 'Empty response',
            detail: 'The server returned no trace payload for this ID.'
          })
        }
      } catch (e: unknown) {
        setLoadError(formatTraceApiError(e))
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const jsonText = useMemo(() => (trace ? JSON.stringify(trace, null, 2) : ''), [trace])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 text-brand-text dark:text-gray-100">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Link
          to="/automations"
          className="inline-flex items-center gap-1.5 text-sm text-brand-text/70 hover:text-brand-primary dark:text-gray-400 dark:hover:text-brand-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Automations
        </Link>
        <span className="text-brand-text/30 dark:text-gray-600">|</span>
        <Link
          to="/dashboard"
          className="text-sm text-brand-text/70 hover:text-brand-primary dark:text-gray-400 dark:hover:text-brand-accent"
        >
          Dashboard
        </Link>
      </div>

      <div className="flex items-start gap-3">
        <GitBranch className="mt-0.5 h-6 w-6 shrink-0 text-brand-primary" />
        <div>
          <h1 className="text-xl font-semibold text-brand-text dark:text-white">
            Correlation trace (internal)
          </h1>
          <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-400">
            Tenant-scoped stitched view for one <code className="rounded bg-brand-text/10 px-1 text-xs">correlation_id</code>.
            See{' '}
            <code className="rounded bg-brand-text/10 px-1 text-xs">docs/CORRELATION_AND_EVENTS.md</code>.
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-4 rounded-xl border border-brand-text/10 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <label className="block text-xs font-medium text-brand-text/70 dark:text-gray-400">
          Correlation ID
          <input
            type="text"
            className="mt-1 w-full rounded-lg border border-brand-text/20 bg-white px-3 py-2 font-mono text-sm text-brand-text focus:border-brand-accent focus:ring-brand-accent dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
            placeholder="Paste UUID or value from API / X-Correlation-ID"
            value={correlationInput}
            onChange={(e) => setCorrelationInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && correlationInput.trim() && !loading) {
                void loadTrace(correlationInput)
              }
            }}
          />
        </label>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={loading || !correlationInput.trim()}
            className="inline-flex items-center gap-1.5 rounded-md border border-brand-primary/40 bg-brand-primary/10 px-3 py-2 text-sm font-medium text-brand-primary disabled:opacity-50"
            onClick={() => void loadTrace(correlationInput)}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? 'Loading…' : 'Load trace'}
          </button>
          <button
            type="button"
            disabled={!correlationInput.trim()}
            className="rounded-md border border-brand-text/20 px-3 py-2 text-sm font-medium text-brand-text hover:bg-brand-text/5 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700/50"
            onClick={() => {
              void navigator.clipboard.writeText(correlationInput.trim())
              addToast({ type: 'success', title: 'Copied correlation ID' })
            }}
          >
            <span className="inline-flex items-center gap-1.5">
              <Copy className="h-4 w-4" />
              Copy ID
            </span>
          </button>
          {lastPresetId ? (
            <button
              type="button"
              className="rounded-md border border-brand-text/20 px-3 py-2 text-sm font-medium text-brand-text hover:bg-brand-text/5 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700/50"
              onClick={() => {
                setCorrelationInput(lastPresetId)
                void loadTrace(lastPresetId)
              }}
            >
              Use last preset run ID
            </button>
          ) : null}
        </div>

        {loadError ? (
          <div
            className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-950 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100"
            role="alert"
          >
            <p className="font-medium">{loadError.title}</p>
            <p className="mt-0.5 text-xs opacity-90">{loadError.detail}</p>
          </div>
        ) : null}

        {timeline.length > 0 ? (
          <div className="rounded-md border border-brand-text/10 dark:border-gray-600">
            <p className="border-b border-brand-text/10 px-3 py-2 text-xs font-medium uppercase tracking-wide text-brand-text/60 dark:border-gray-600 dark:text-gray-400">
              Timeline (newest first)
            </p>
            <ul className="max-h-72 overflow-auto text-sm">
              {timeline.slice(0, 100).map((row, i) => {
                const ql = getTraceRowQuickLink(row.raw)
                return (
                  <li
                    key={`${row.at}-${row.title}-${i}`}
                    className="border-b border-brand-text/5 px-3 py-2 last:border-0 dark:border-gray-700/50"
                  >
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="rounded bg-brand-text/10 px-1.5 py-0.5 font-medium text-[10px] text-brand-text dark:bg-gray-700 dark:text-gray-200">
                        {row.domain}
                      </span>
                      <span className="font-medium">{row.title}</span>
                      {row.subtitle ? (
                        <span className="text-xs text-brand-text/60 dark:text-gray-400">
                          · {row.subtitle}
                        </span>
                      ) : null}
                    </div>
                    {row.at ? (
                      <p className="mt-0.5 text-[11px] text-brand-text/50 dark:text-gray-500">
                        {row.at}
                      </p>
                    ) : null}
                    {ql ? (
                      <Link
                        to={ql.to}
                        className="mt-1 inline-block text-xs font-medium text-brand-primary hover:underline dark:text-brand-accent"
                      >
                        {ql.label} →
                      </Link>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          </div>
        ) : trace && !loadError ? (
          <p className="text-sm text-brand-text/60 dark:text-gray-400">
            No timeline rows in sections (empty trace for this tenant/ID).
          </p>
        ) : null}

        {trace ? (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md border border-brand-text/20 px-3 py-1.5 text-xs font-medium text-brand-text hover:bg-brand-text/5 dark:border-gray-600 dark:text-gray-200"
                onClick={() => {
                  void navigator.clipboard.writeText(jsonText)
                  addToast({ type: 'success', title: 'Copied JSON' })
                }}
              >
                <span className="inline-flex items-center gap-1.5">
                  <Copy className="h-3.5 w-3.5" />
                  Copy full JSON
                </span>
              </button>
            </div>
            <details className="rounded-md border border-dashed border-brand-text/20 dark:border-gray-600">
              <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-brand-text dark:text-gray-200">
                Raw JSON
              </summary>
              <pre className="max-h-80 overflow-auto border-t border-brand-text/10 p-3 font-mono text-[11px] leading-snug dark:border-gray-600">
                {jsonText}
              </pre>
            </details>
          </div>
        ) : null}
      </div>
    </div>
  )
}
