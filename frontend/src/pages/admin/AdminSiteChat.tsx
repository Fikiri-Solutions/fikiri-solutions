import { useEffect, useId, useRef, useState } from 'react'
import { Download, MessageSquare, RefreshCw } from 'lucide-react'
import { apiClient } from '../../services/apiClient'
import type {
  SiteChatMessage,
  SiteChatSessionDetail,
  SiteChatSessionSummary,
} from '../../types/admin'
import { AdminPanel, StatusBadge, toneForStatusLabel, type StatusTone } from './adminUi'

const PAGE_SIZE = 25

function tierTone(tier?: string | null): StatusTone {
  const t = (tier || '').toLowerCase()
  if (t === 'hot' || t === 'qualified' || t === 'strong') return 'ok'
  if (t === 'possible' || t === 'warm') return 'warn'
  if (t === 'cold' || t === 'spam') return 'neutral'
  return 'unknown'
}

function formatWhen(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString()
}

function downloadBlob(filename: string, body: string, mime: string) {
  const blob = new Blob([body], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function MessageBubble({ msg }: { msg: SiteChatMessage }) {
  const isUser = (msg.role || '').toLowerCase() === 'user'
  return (
    <div
      className={[
        'rounded-lg border px-3 py-2 text-sm',
        isUser
          ? 'border-teal-200 bg-teal-50/80 dark:border-teal-900 dark:bg-teal-950/40'
          : 'border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800/60',
      ].join(' ')}
    >
      <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-zinc-500">
        <span>{isUser ? 'Visitor' : 'Bot'}</span>
        {msg.mode ? <span className="normal-case tracking-normal">· {msg.mode}</span> : null}
        {msg.created_at ? (
          <span className="ml-auto normal-case font-normal tracking-normal">
            {formatWhen(msg.created_at)}
          </span>
        ) : null}
      </div>
      <p className="whitespace-pre-wrap break-words text-zinc-900 dark:text-zinc-100">{msg.content}</p>
      {!isUser && (msg.grounded != null || msg.lead_assessment) ? (
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-500">
          {msg.grounded != null ? (
            <span>grounded: {msg.grounded ? 'yes' : 'no'}</span>
          ) : null}
          {msg.confidence != null ? <span>confidence: {msg.confidence}</span> : null}
          {msg.lead_assessment?.tier ? (
            <span>
              lead: {msg.lead_assessment.tier}
              {msg.lead_assessment.score != null ? ` (${msg.lead_assessment.score})` : ''}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export function AdminSiteChat() {
  const [sessions, setSessions] = useState<SiteChatSessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<SiteChatSessionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [exportBusy, setExportBusy] = useState(false)
  const [exportMessage, setExportMessage] = useState<string | null>(null)
  const [detailEpoch, setDetailEpoch] = useState(0)
  const requestSeq = useRef(0)
  const listId = useId()

  const apiErrorMessage = (err: unknown, fallback: string): string => {
    if (err && typeof err === 'object' && 'response' in err) {
      const data = (err as { response?: { data?: { error?: string; message?: string } } })
        .response?.data
      if (data?.error) return String(data.error)
      if (data?.message) return String(data.message)
    }
    if (err && typeof err === 'object' && 'message' in err) {
      return String((err as { message?: string }).message)
    }
    return fallback
  }

  const loadList = (nextOffset = offset, reloadSelected = false) => {
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    void apiClient
      .listSiteChatSessions({ limit: PAGE_SIZE, offset: nextOffset })
      .then((result) => {
        if (seq !== requestSeq.current) return
        setSessions(result.sessions || [])
        setTotal(result.total ?? 0)
        setOffset(result.offset ?? nextOffset)
        if (reloadSelected && selectedId) {
          setDetailEpoch((n) => n + 1)
        }
      })
      .catch((err: unknown) => {
        if (seq !== requestSeq.current) return
        setError(apiErrorMessage(err, 'Failed to load sessions'))
        setSessions([])
        setTotal(0)
      })
      .finally(() => {
        if (seq === requestSeq.current) setLoading(false)
      })
  }

  useEffect(() => {
    loadList(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial mount only
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      setDetailError(null)
      return
    }
    let cancelled = false
    setDetailLoading(true)
    setDetailError(null)
    void apiClient
      .getSiteChatSession(selectedId)
      .then((result) => {
        if (!cancelled) setDetail(result)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setDetail(null)
        setDetailError(apiErrorMessage(err, 'Failed to load transcript'))
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId, detailEpoch])

  const handleExport = async (format: 'text' | 'json') => {
    if (!selectedId) return
    setExportBusy(true)
    setExportMessage(null)
    try {
      const exported = await apiClient.exportSiteChatSession(selectedId, format)
      const body =
        format === 'text'
          ? String(exported.content || '')
          : JSON.stringify(exported, null, 2)
      const ext = format === 'text' ? 'txt' : 'json'
      const mime = format === 'text' ? 'text/plain;charset=utf-8' : 'application/json'
      const safeId = selectedId.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(0, 120)
      downloadBlob(`site-chat-${safeId}.${ext}`, body, mime)
      setExportMessage(`Downloaded ${ext.toUpperCase()} for ${selectedId}`)
    } catch {
      setExportMessage('Download failed. Try again.')
    } finally {
      setExportBusy(false)
    }
  }

  const pageStart = total === 0 ? 0 : offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)
  const canPrev = offset > 0
  const canNext = offset + PAGE_SIZE < total

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Site Chat Logs</h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Landing-page chatbot sessions from fikiriSolutions.com. Open a session to review Q&amp;A,
          then download a copy-friendly transcript.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <AdminPanel
          title="Sessions"
          description={
            loading
              ? 'Loading…'
              : total > 0
                ? `Showing ${pageStart}–${pageEnd} of ${total}`
                : 'No sessions stored yet'
          }
          right={
            <button
              type="button"
              onClick={() => loadList(offset, true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800"
              disabled={loading}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden />
              Refresh
            </button>
          }
        >
          {error ? (
            <p className="text-sm text-red-700 dark:text-red-300" role="alert">
              {error}
            </p>
          ) : null}

          {!loading && !error && sessions.length === 0 ? (
            <p className="text-sm text-zinc-500">
              Transcripts appear here once visitors chat and persistence is enabled on the backend.
            </p>
          ) : null}

          <ul id={listId} className="divide-y divide-zinc-100 dark:divide-zinc-800" role="list">
            {sessions.map((session) => {
              const active = session.session_id === selectedId
              return (
                <li key={session.session_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(session.session_id)}
                    className={[
                      'flex w-full flex-col gap-1 px-1 py-3 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600',
                      active
                        ? 'bg-teal-50/80 dark:bg-teal-950/40'
                        : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50',
                    ].join(' ')}
                    aria-current={active ? 'true' : undefined}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <MessageSquare className="h-3.5 w-3.5 shrink-0 text-teal-700 dark:text-teal-400" aria-hidden />
                      <span className="truncate font-mono text-xs text-zinc-800 dark:text-zinc-200">
                        {session.session_id}
                      </span>
                      {session.latest_lead_tier ? (
                        <StatusBadge
                          label={session.latest_lead_tier}
                          tone={tierTone(session.latest_lead_tier)}
                        />
                      ) : null}
                      {session.last_mode ? (
                        <StatusBadge
                          label={session.last_mode}
                          tone={toneForStatusLabel(session.last_mode)}
                        />
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-zinc-500">
                      <span>{session.turn_count ?? 0} turns</span>
                      <span>{formatWhen(session.last_seen_at)}</span>
                    </div>
                    {session.latest_lead_synopsis ? (
                      <p className="line-clamp-2 text-xs text-zinc-600 dark:text-zinc-400">
                        {session.latest_lead_synopsis}
                      </p>
                    ) : null}
                  </button>
                </li>
              )
            })}
          </ul>

          {total > PAGE_SIZE ? (
            <div className="mt-3 flex items-center justify-between gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
              <button
                type="button"
                disabled={!canPrev || loading}
                onClick={() => loadList(Math.max(0, offset - PAGE_SIZE))}
                className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium disabled:opacity-40 dark:border-zinc-700"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!canNext || loading}
                onClick={() => loadList(offset + PAGE_SIZE)}
                className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium disabled:opacity-40 dark:border-zinc-700"
              >
                Next
              </button>
            </div>
          ) : null}
        </AdminPanel>

        <AdminPanel
          title="Transcript"
          description={
            selectedId
              ? `Session ${selectedId}`
              : 'Select a session to read the conversation'
          }
          right={
            selectedId ? (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={exportBusy}
                  onClick={() => void handleExport('text')}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
                >
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  Download .txt
                </button>
                <button
                  type="button"
                  disabled={exportBusy}
                  onClick={() => void handleExport('json')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800"
                >
                  Download .json
                </button>
              </div>
            ) : null
          }
        >
          {exportMessage ? (
            <p className="mb-3 text-xs text-zinc-600 dark:text-zinc-400" role="status">
              {exportMessage}
            </p>
          ) : null}

          {!selectedId ? (
            <p className="text-sm text-zinc-500">Choose a session from the list.</p>
          ) : null}
          {detailLoading ? <p className="text-sm text-zinc-500">Loading transcript…</p> : null}
          {detailError ? (
            <p className="text-sm text-red-700 dark:text-red-300" role="alert">
              {detailError}
            </p>
          ) : null}

          {detail && !detailLoading ? (
            <div className="space-y-4">
              <dl className="grid gap-2 text-xs sm:grid-cols-2">
                <div>
                  <dt className="text-zinc-500">First seen</dt>
                  <dd>{formatWhen(detail.session.first_seen_at)}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Last seen</dt>
                  <dd>{formatWhen(detail.session.last_seen_at)}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Source page</dt>
                  <dd className="break-all">{detail.session.source_page || '—'}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Handoff</dt>
                  <dd>{detail.session.latest_handoff_path || '—'}</dd>
                </div>
              </dl>
              <div className="space-y-2">
                {(detail.messages || []).map((msg, idx) => (
                  <MessageBubble key={`${msg.role}-${idx}-${msg.created_at || ''}`} msg={msg} />
                ))}
                {(detail.messages || []).length === 0 ? (
                  <p className="text-sm text-zinc-500">No messages in this session.</p>
                ) : null}
              </div>
            </div>
          ) : null}
        </AdminPanel>
      </div>
    </div>
  )
}
