import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { AdminReauthModal } from '../../components/AdminReauthModal'
import type { AdminAuditEntry } from '../../types/admin'
import { AdminPanel, StatusBadge, type StatusTone } from './adminUi'
import {
  abbreviateCorrelation,
  auditCopySummaryLine,
  buildAuditDetailFields,
  controlledReasonCode,
  targetLabel,
} from './adminAuditSanitize'

const PAGE_SIZE = 50
const OUTCOME_OPTIONS = ['', 'success', 'denied', 'error'] as const

type AuditFilters = {
  outcome: string
  actor: string
  targetType: string
  targetId: string
}

function parseFilters(params: URLSearchParams): AuditFilters {
  const outcome = (params.get('outcome') || '').trim().toLowerCase()
  return {
    outcome: OUTCOME_OPTIONS.includes(outcome as (typeof OUTCOME_OPTIONS)[number])
      ? outcome
      : '',
    actor: (params.get('actor') || '').trim(),
    targetType: (params.get('target_type') || '').trim().slice(0, 64),
    targetId: (params.get('target_id') || '').trim().slice(0, 128),
  }
}

function parseOffset(params: URLSearchParams): number {
  const raw = params.get('offset')
  if (!raw) return 0
  const n = Number.parseInt(raw, 10)
  if (!Number.isFinite(n) || n < 0) return 0
  return n
}

function outcomeTone(outcome?: string | null): StatusTone {
  const o = (outcome || '').toLowerCase()
  if (o === 'success') return 'ok'
  if (o === 'denied' || o === 'failure' || o === 'error') return 'bad'
  return 'neutral'
}

async function copyText(value: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value)
      return true
    } catch {
      return false
    }
  }
  try {
    const area = document.createElement('textarea')
    area.value = value
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.left = '-9999px'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(area)
    return ok
  } catch {
    return false
  }
}

export function AdminAuditLog() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = parseFilters(searchParams)
  const offset = parseOffset(searchParams)

  const [draft, setDraft] = useState<AuditFilters>(filters)
  const [items, setItems] = useState<AdminAuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<AdminAuditEntry | null>(null)
  const [copyStatus, setCopyStatus] = useState<string>('')
  const [exportBusy, setExportBusy] = useState(false)
  const [showExportStepUp, setShowExportStepUp] = useState(false)
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json')
  const [exportMessage, setExportMessage] = useState<string | null>(null)
  const detailsBtnRefs = useRef<Map<number, HTMLButtonElement>>(new Map())
  const closeBtnRef = useRef<HTMLButtonElement | null>(null)
  const requestSeq = useRef(0)
  const titleId = useId()
  const liveId = useId()

  useEffect(() => {
    setDraft(filters)
  }, [filters.outcome, filters.actor, filters.targetType, filters.targetId])

  useEffect(() => {
    let cancelled = false
    const seq = ++requestSeq.current

    setLoading(true)
    setError(null)

    const actorParsed = Number.parseInt(filters.actor, 10)
    const params: Parameters<typeof apiClient.listAdminAudit>[0] = {
      limit: PAGE_SIZE,
      offset,
    }
    if (filters.outcome) params.outcome = filters.outcome
    if (filters.actor && Number.isFinite(actorParsed) && actorParsed > 0) {
      params.actor_user_id = actorParsed
    }
    if (filters.targetType) params.target_type = filters.targetType
    if (filters.targetId) params.target_id = filters.targetId

    void apiClient
      .listAdminAudit(params)
      .then((result) => {
        if (cancelled || requestSeq.current !== seq) return
        setItems((result.items || []) as AdminAuditEntry[])
        setTotal(typeof result.total === 'number' ? result.total : 0)
      })
      .catch((err: unknown) => {
        if (cancelled || requestSeq.current !== seq) return
        setError(err instanceof Error ? err.message : 'Failed to load audit log')
        setItems([])
        setTotal(0)
      })
      .finally(() => {
        if (cancelled || requestSeq.current !== seq) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [filters.outcome, filters.actor, filters.targetType, filters.targetId, offset])

  const writeParams = useCallback(
    (next: AuditFilters, nextOffset: number) => {
      const params = new URLSearchParams()
      if (next.outcome) params.set('outcome', next.outcome)
      if (next.actor.trim()) params.set('actor', next.actor.trim())
      if (next.targetType.trim()) params.set('target_type', next.targetType.trim())
      if (next.targetId.trim()) params.set('target_id', next.targetId.trim())
      if (nextOffset > 0) params.set('offset', String(nextOffset))
      setSearchParams(params, { replace: false })
    },
    [setSearchParams],
  )

  const applyFilters = (event: FormEvent) => {
    event.preventDefault()
    writeParams(
      {
        outcome: draft.outcome,
        actor: draft.actor.trim(),
        targetType: draft.targetType.trim(),
        targetId: draft.targetId.trim(),
      },
      0,
    )
  }

  const clearFilters = () => {
    setDraft({ outcome: '', actor: '', targetType: '', targetId: '' })
    writeParams({ outcome: '', actor: '', targetType: '', targetId: '' }, 0)
  }

  const openDetails = (entry: AdminAuditEntry) => {
    setCopyStatus('')
    setSelected(entry)
  }

  const closeDetails = useCallback(() => {
    const id = selected?.id
    setSelected(null)
    setCopyStatus('')
    if (id != null) {
      window.requestAnimationFrame(() => {
        detailsBtnRefs.current.get(id)?.focus()
      })
    }
  }, [selected?.id])

  useEffect(() => {
    if (!selected) return
    closeBtnRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeDetails()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, closeDetails])

  const announceCopy = async (label: string, value: string) => {
    const ok = await copyText(value)
    setCopyStatus(ok ? `${label} copied` : `Could not copy ${label.toLowerCase()}`)
  }

  const pageStart = total === 0 ? 0 : offset + 1
  const pageEnd = Math.min(offset + items.length, total)
  const canPrev = offset > 0
  const canNext = offset + PAGE_SIZE < total

  return (
    <div className="space-y-4">
      <AdminPanel
        title="Audit Log"
        headingAs="h2"
        description="Investigate platform operator and security actions. Filters run on the server."
      >
        <form
          className="grid gap-3 rounded-lg border border-zinc-200 bg-zinc-50/60 p-3 dark:border-zinc-800 dark:bg-zinc-950/40 sm:grid-cols-2 lg:grid-cols-4"
          onSubmit={applyFilters}
          aria-label="Audit filters"
        >
          <label className="block text-sm">
            <span className="text-xs font-medium text-zinc-500">Outcome</span>
            <select
              className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              value={draft.outcome}
              onChange={(e) => setDraft((d) => ({ ...d, outcome: e.target.value }))}
            >
              <option value="">Any</option>
              <option value="success">success</option>
              <option value="denied">denied</option>
              <option value="error">error</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-xs font-medium text-zinc-500">Actor user ID</span>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="off"
              className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              value={draft.actor}
              onChange={(e) => setDraft((d) => ({ ...d, actor: e.target.value }))}
              placeholder="e.g. 9"
            />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-medium text-zinc-500">Target type</span>
            <input
              type="text"
              autoComplete="off"
              className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              value={draft.targetType}
              onChange={(e) => setDraft((d) => ({ ...d, targetType: e.target.value }))}
              placeholder="e.g. user, tenant"
            />
          </label>
          <label className="block text-sm">
            <span className="text-xs font-medium text-zinc-500">Target ID</span>
            <input
              type="text"
              autoComplete="off"
              className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              value={draft.targetId}
              onChange={(e) => setDraft((d) => ({ ...d, targetId: e.target.value }))}
              placeholder="e.g. 5"
            />
          </label>
          <div className="flex flex-wrap items-end gap-2 sm:col-span-2 lg:col-span-4">
            <button
              type="submit"
              className="rounded-md bg-teal-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
            >
              Apply filters
            </button>
            <button
              type="button"
              onClick={clearFilters}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-700 dark:text-zinc-200"
            >
              Clear
            </button>
            <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
              <span className="text-xs font-medium text-zinc-500">Export</span>
              <select
                className="rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value === 'csv' ? 'csv' : 'json')}
                aria-label="Export format"
              >
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
              </select>
            </label>
            <button
              type="button"
              disabled={exportBusy || loading}
              onClick={() => {
                setExportMessage(null)
                setShowExportStepUp(true)
              }}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-800 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-100"
            >
              Export filtered page
            </button>
            <p className="text-xs text-zinc-500">
              Export is step-up gated, capped at 200 allowlisted rows. No raw metadata.
            </p>
          </div>
        </form>

        {exportMessage ? <p className="mt-3 text-sm text-emerald-700">{exportMessage}</p> : null}
        {loading ? <p className="mt-4 text-sm text-zinc-500">Loading audit events…</p> : null}
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}

        {!loading && !error ? (
          <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-300" aria-live="polite">
            {total === 0
              ? 'No audit events match these filters.'
              : `Showing ${pageStart}–${pageEnd} of ${total}`}
          </p>
        ) : null}

        <div className="mt-3 overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="min-w-full text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
              <tr>
                <th className="px-4 py-2.5">When</th>
                <th className="px-4 py-2.5">Actor</th>
                <th className="px-4 py-2.5">Action</th>
                <th className="px-4 py-2.5">Target</th>
                <th className="px-4 py-2.5">Outcome</th>
                <th className="px-4 py-2.5">Reason</th>
                <th className="px-4 py-2.5">Correlation</th>
                <th className="px-4 py-2.5">Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((entry) => {
                const reason = controlledReasonCode(entry) || '—'
                return (
                  <tr
                    key={entry.id}
                    className="border-t border-zinc-100 hover:bg-zinc-50/80 dark:border-zinc-800 dark:hover:bg-zinc-950/50"
                  >
                    <td className="whitespace-nowrap px-4 py-2.5 text-zinc-700 dark:text-zinc-300">
                      {entry.created_at || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-zinc-700 dark:text-zinc-300">
                      #{entry.actor_user_id}
                    </td>
                    <td className="max-w-[14rem] break-words px-4 py-2.5 font-mono text-xs text-zinc-900 dark:text-zinc-100">
                      {entry.action || '—'}
                    </td>
                    <td className="max-w-[12rem] break-words px-4 py-2.5 text-zinc-700 dark:text-zinc-300">
                      {targetLabel(entry)}
                    </td>
                    <td className="px-4 py-2.5">
                      {entry.outcome ? (
                        <StatusBadge label={entry.outcome} tone={outcomeTone(entry.outcome)} />
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="max-w-[10rem] break-words px-4 py-2.5 font-mono text-xs text-zinc-700 dark:text-zinc-300">
                      {reason}
                    </td>
                    <td
                      className="max-w-[8rem] break-all px-4 py-2.5 font-mono text-xs text-zinc-500"
                      title={entry.correlation_id || undefined}
                    >
                      {abbreviateCorrelation(entry.correlation_id)}
                    </td>
                    <td className="px-4 py-2.5">
                      <button
                        type="button"
                        className="text-sm font-medium text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
                        ref={(node) => {
                          if (node) detailsBtnRefs.current.set(entry.id, node)
                          else detailsBtnRefs.current.delete(entry.id)
                        }}
                        onClick={() => openDetails(entry)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                )
              })}
              {!loading && items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-zinc-500">
                    {error ? '—' : 'No audit events yet.'}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!canPrev || loading}
            className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-zinc-700"
            onClick={() => writeParams(filters, Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </button>
          <button
            type="button"
            disabled={!canNext || loading}
            className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-zinc-700"
            onClick={() => writeParams(filters, offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      </AdminPanel>

      {selected ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40" role="presentation">
          <button
            type="button"
            className="absolute inset-0 cursor-default"
            aria-label="Close event details"
            onClick={closeDetails}
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-zinc-200 bg-white shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div className="flex items-start justify-between gap-3 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
              <div className="min-w-0">
                <h3 id={titleId} className="text-base font-semibold tracking-tight">
                  Event details
                </h3>
                <p className="mt-0.5 break-words font-mono text-xs text-zinc-500">
                  {selected.action || '—'}
                </p>
              </div>
              <button
                ref={closeBtnRef}
                type="button"
                onClick={closeDetails}
                className="rounded-md border border-zinc-300 px-2 py-1 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-700"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              <dl className="space-y-3 text-sm">
                {buildAuditDetailFields(selected).map((field) => (
                  <div key={field.key}>
                    <dt className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                      {field.label}
                    </dt>
                    <dd className="mt-0.5 break-words text-zinc-900 dark:text-zinc-100">
                      {field.key === 'outcome' ? (
                        <StatusBadge label={field.value} tone={outcomeTone(field.value)} />
                      ) : (
                        field.value
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="space-y-2 border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
              <p id={liveId} role="status" aria-live="polite" className="min-h-[1rem] text-xs text-zinc-600 dark:text-zinc-300">
                {copyStatus}
              </p>
              {selected.correlation_id ? (
                <button
                  type="button"
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-zinc-700 dark:hover:bg-zinc-800"
                  onClick={() =>
                    void announceCopy('Correlation ID', String(selected.correlation_id).trim())
                  }
                >
                  Copy correlation ID
                </button>
              ) : null}
              <button
                type="button"
                className="w-full rounded-md bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
                onClick={() => void announceCopy('Event summary', auditCopySummaryLine(selected))}
              >
                Copy sanitized summary
              </button>
            </div>
          </aside>
        </div>
      ) : null}

      <AdminReauthModal
        open={showExportStepUp}
        title="Confirm identity to export audit page"
        busy={exportBusy}
        error={error}
        onCancel={() => {
          if (!exportBusy) setShowExportStepUp(false)
        }}
        onConfirm={async (password, mfaCode, recoveryCode) => {
          setExportBusy(true)
          setError(null)
          try {
            const stepUp = await apiClient.reauthenticateAdmin({
              password,
              mfa_code: mfaCode,
              recovery_code: recoveryCode,
            })
            if (!stepUp?.step_up_confirmed) {
              throw new Error('Step-up authentication required')
            }
            const actorParsed = Number.parseInt(filters.actor, 10)
            const exported = await apiClient.exportAdminAudit({
              format: exportFormat,
              limit: PAGE_SIZE,
              offset,
              outcome: filters.outcome || undefined,
              actor_user_id:
                filters.actor && Number.isFinite(actorParsed) && actorParsed > 0
                  ? actorParsed
                  : undefined,
              target_type: filters.targetType || undefined,
              target_id: filters.targetId || undefined,
            })
            const blob = new Blob([exported.body || ''], {
              type: exported.content_type || 'application/octet-stream',
            })
            const url = URL.createObjectURL(blob)
            const anchor = document.createElement('a')
            anchor.href = url
            anchor.download =
              exportFormat === 'csv' ? 'fikiri-audit-export.csv' : 'fikiri-audit-export.json'
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
            URL.revokeObjectURL(url)
            setExportMessage(`Exported ${exported.count} allowlisted row(s).`)
            setShowExportStepUp(false)
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Export failed')
          } finally {
            setExportBusy(false)
          }
        }}
      />
    </div>
  )
}
