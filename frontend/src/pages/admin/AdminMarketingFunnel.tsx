import { useEffect, useState } from 'react'
import { BarChart3 } from 'lucide-react'
import { apiClient } from '../../services/apiClient'
import { AdminPanel, MetricTile } from './adminUi'

type FunnelSummary = {
  lookback_days: number
  events_enabled: boolean
  events_available: boolean
  counts: Record<string, number>
  intake: {
    starts: number
    submitted_events: number
    completion_rate: number | null
    step_views: Record<string, number>
    crm_submissions: number
    crm_by_source: Record<string, number>
    crm_by_priority: Record<string, number>
    crm_available: boolean
  }
  chatbot: {
    opened: number
    first_message: number
    fallback: number
    handoff: number
    active_rate: number | null
  }
  notes?: string[]
}

function pct(rate: number | null | undefined): string {
  if (rate == null || Number.isNaN(rate)) return '—'
  return `${(rate * 100).toFixed(1)}%`
}

export function AdminMarketingFunnel() {
  const [lookbackDays, setLookbackDays] = useState(7)
  const [summary, setSummary] = useState<FunnelSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void apiClient
      .getMarketingFunnelSummary(lookbackDays)
      .then((result) => {
        if (!cancelled) setSummary(result as FunnelSummary)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load marketing funnel')
          setSummary(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lookbackDays])

  const stepEntries = Object.entries(summary?.intake.step_views || {})
  const sourceEntries = Object.entries(summary?.intake.crm_by_source || {})
  const priorityEntries = Object.entries(summary?.intake.crm_by_priority || {})

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-teal-700 dark:text-teal-400" aria-hidden />
            <h2 className="text-xl font-semibold tracking-tight">Marketing funnel</h2>
          </div>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
            First-party intake and chatbot events (Vercel Web Analytics off; Speed Insights free
            tier only). Abandonment is inferred from starts vs completions.
          </p>
        </div>
        <label className="text-sm text-zinc-600 dark:text-zinc-400">
          Lookback
          <select
            className="ml-2 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            value={lookbackDays}
            onChange={(e) => setLookbackDays(Number(e.target.value))}
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </label>
      </div>

      {loading && (
        <p className="text-sm text-zinc-500" role="status">
          Loading funnel…
        </p>
      )}
      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      {summary && !loading && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricTile label="Intake starts" value={String(summary.intake.starts)} />
            <MetricTile
              label="Intake submitted (events)"
              value={String(summary.intake.submitted_events)}
            />
            <MetricTile label="Completion rate" value={pct(summary.intake.completion_rate)} />
            <MetricTile
              label="CRM submissions"
              value={String(summary.intake.crm_submissions)}
              hint={summary.intake.crm_available ? 'Authoritative' : 'Unavailable'}
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricTile label="Chatbot opened" value={String(summary.chatbot.opened)} />
            <MetricTile label="First message" value={String(summary.chatbot.first_message)} />
            <MetricTile label="Fallback replies" value={String(summary.chatbot.fallback)} />
            <MetricTile
              label="Handoff clicks"
              value={String(summary.chatbot.handoff)}
              hint={`Active ${pct(summary.chatbot.active_rate)}`}
            />
          </div>

          <AdminPanel title="Drop-off by intake step">
            {stepEntries.length === 0 ? (
              <p className="text-sm text-zinc-500">No step views in this window.</p>
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {stepEntries.map(([step, count]) => (
                  <li
                    key={step}
                    className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
                  >
                    <span className="font-medium">{step}</span>
                    <span className="tabular-nums text-zinc-600 dark:text-zinc-300">{count}</span>
                  </li>
                ))}
              </ul>
            )}
          </AdminPanel>

          <div className="grid gap-6 lg:grid-cols-2">
            <AdminPanel title="CRM leads by source">
              {sourceEntries.length === 0 ? (
                <p className="text-sm text-zinc-500">No consultation intake rows in this window.</p>
              ) : (
                <ul className="space-y-2">
                  {sourceEntries.map(([source, count]) => (
                    <li key={source} className="flex justify-between text-sm">
                      <span className="truncate pr-3">{source}</span>
                      <span className="tabular-nums">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </AdminPanel>
            <AdminPanel title="Priority band (CRM metadata)">
              {priorityEntries.length === 0 ? (
                <p className="text-sm text-zinc-500">No priority bands recorded yet.</p>
              ) : (
                <ul className="space-y-2">
                  {priorityEntries.map(([band, count]) => (
                    <li key={band} className="flex justify-between text-sm">
                      <span>{band}</span>
                      <span className="tabular-nums">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </AdminPanel>
          </div>

          {(summary.notes || []).length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs text-zinc-500">
              {summary.notes?.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
