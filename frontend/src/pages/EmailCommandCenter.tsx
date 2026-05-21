import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, Inbox, Loader2, RefreshCw, Sparkles } from 'lucide-react'
import { apiClient } from '../services/apiClient'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/Toast'
import { EmptyState } from '../components/EmptyState'
import { loadGmailLookbackId } from '../utils/gmailLookbackStorage'
import type { TriageCategoryId } from '../constants/emailCommandCenterTabs'
import {
  humanPriorityTag,
  MARK_DONE_BACKEND_ACTION,
  MARK_DONE_UNDO_MS,
  NOT_SURE_CATEGORY,
  ORGANIZE_QUEUES,
  ORGANIZE_TRUST_LINES,
  organizeAttentionCount,
  RESTORE_TO_QUEUE_BACKEND_ACTION,
  type OrganizeBulkActionId,
  type OrganizeQueueAction,
  type OrganizeQueueId,
  priorityTagClass,
  queueCount,
  QUEUE_ACTIONS,
} from '../constants/inboxSimpleFirst'

export interface TriageListEmail {
  id: string
  from: string
  subject: string
  category: string
  lead_score: number
  urgency_score: number
  cleanup_action: string
  confidence: number
  reason: string
}

function normalizeRow(raw: Record<string, unknown>): TriageListEmail | null {
  const id = raw.id != null ? String(raw.id) : ''
  if (!id) return null
  return {
    id,
    from: String(raw.from ?? ''),
    subject: String(raw.subject ?? '(No subject)'),
    category: String(raw.category ?? ''),
    lead_score: Number(raw.lead_score ?? 0),
    urgency_score: Number(raw.urgency_score ?? 0),
    cleanup_action: String(raw.cleanup_action ?? 'keep'),
    confidence: Number(raw.confidence ?? 0),
    reason: String(raw.reason ?? ''),
  }
}

function queueDef(queue: OrganizeQueueId) {
  const def = ORGANIZE_QUEUES.find((q) => q.id === queue)
  if (!def) {
    throw new Error(`Unknown organize queue: ${queue}`)
  }
  return def
}

function categoriesForQueue(queue: OrganizeQueueId): TriageCategoryId[] {
  if (queue === 'not_sure') return [NOT_SURE_CATEGORY]
  return queueDef(queue).categories
}

export const EmailCommandCenter: React.FC = () => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const [activeQueue, setActiveQueue] = useState<OrganizeQueueId>('opportunities')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [syncPending, setSyncPending] = useState(false)
  const [expandedReasonId, setExpandedReasonId] = useState<string | null>(null)
  const prevSyncingRef = useRef(false)
  const lastMarkDoneIdsRef = useRef<string[]>([])

  const { data: syncStatus } = useQuery({
    queryKey: ['gmail-sync-status', user?.id],
    queryFn: () => apiClient.getEmailSyncStatus(),
    enabled: !!user,
    staleTime: 10_000,
    refetchInterval: (query) => (query.state.data?.syncing ? 3000 : 15_000),
  })

  const { data: summaryData, refetch: refetchSummary } = useQuery({
    queryKey: ['email-triage-summary', user?.id],
    queryFn: () => apiClient.getEmailTriage({ category: 'business_lead', limit: 1 }),
    enabled: !!user,
    staleTime: 30_000,
  })

  const categoryCounts = summaryData?.category_counts ?? {}
  const unclassifiedCount = summaryData?.unclassified_synced_count ?? 0
  const activeCategories = categoriesForQueue(activeQueue)

  const listQueries = useQueries({
    queries: activeCategories.map((category) => ({
      queryKey: ['email-triage', activeQueue, category, user?.id],
      queryFn: () => apiClient.getEmailTriage({ category, limit: 20 }),
      enabled: !!user,
      staleTime: 30_000,
    })),
  })

  const syncing = Boolean(syncStatus?.syncing)
  const isListLoading = listQueries.some((q) => q.isLoading)
  const isListFetching = listQueries.some((q) => q.isFetching)

  const emails = useMemo(() => {
    const byId = new Map<string, TriageListEmail>()
    for (const q of listQueries) {
      const rows = (q.data?.emails ?? []) as Record<string, unknown>[]
      for (const raw of rows) {
        const row = normalizeRow(raw)
        if (row) byId.set(row.id, row)
      }
    }
    return Array.from(byId.values())
  }, [listQueries])

  const queueLabel = activeQueue === 'not_sure' ? 'Not sure' : queueDef(activeQueue).label

  const classifyUnclassifiedSilent = useCallback(async () => {
    try {
      await apiClient.classifyEmailTriageUnclassified(50)
    } catch {
      /* next Update & sort will retry */
    }
  }, [])

  const invalidateOrganize = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['email-triage'] })
    queryClient.invalidateQueries({ queryKey: ['email-triage-summary'] })
    void refetchSummary()
  }, [queryClient, refetchSummary])

  useEffect(() => {
    if (prevSyncingRef.current && !syncing) {
      void classifyUnclassifiedSilent().then(() => invalidateOrganize())
    }
    prevSyncingRef.current = syncing
  }, [syncing, classifyUnclassifiedSilent, invalidateOrganize])

  const runUpdateAndSort = useCallback(async () => {
    setSyncPending(true)
    try {
      await apiClient.triggerGmailSync({ lookback: loadGmailLookbackId('90d') })
      addToast({
        type: 'info',
        title: 'Updating your inbox',
        message: 'New mail will appear in your piles when ready.',
      })
      queryClient.invalidateQueries({ queryKey: ['gmail-sync-status', user?.id] })
      await classifyUnclassifiedSilent()
      invalidateOrganize()
    } catch {
      addToast({
        type: 'error',
        title: 'Could not update',
        message: 'Check your Gmail connection and try again.',
      })
    } finally {
      setSyncPending(false)
    }
  }, [addToast, classifyUnclassifiedSilent, invalidateOrganize, queryClient, user?.id])

  const bulkMutation = useMutation({
    mutationFn: async (opts: {
      action: string
      ids: string[]
      confirmDestructive: boolean
    }) =>
      apiClient.emailTriageBulkAction({
        action: opts.action,
        email_ids: opts.ids,
        confirm_destructive: opts.confirmDestructive,
      }),
    onSuccess: (res, vars) => {
      clearSelection()
      invalidateOrganize()
      if (vars.action === MARK_DONE_BACKEND_ACTION) {
        return
      }
      const actionLabel =
        vars.action === RESTORE_TO_QUEUE_BACKEND_ACTION
          ? 'Restored to pile'
          : vars.action === 'archive'
            ? 'Filed away in Gmail'
            : vars.action === 'create_leads'
              ? 'Saved to customers'
              : 'Done'
      addToast({
        type: 'success',
        title: actionLabel,
        message:
          vars.action === 'archive'
            ? 'Still available in Gmail All Mail.'
            : `${res.processed ?? 0} message(s) updated.`,
      })
    },
    onError: () => {
      addToast({ type: 'error', title: 'Something went wrong', message: 'Please try again.' })
    },
  })

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const selectAllVisible = useCallback(() => {
    setSelected(new Set(emails.map((e) => e.id)))
  }, [emails])

  const clearSelection = useCallback(() => setSelected(new Set()), [])

  const restoreMarkDone = useCallback(
    (ids: string[]) => {
      if (ids.length === 0) return
      bulkMutation.mutate({
        action: RESTORE_TO_QUEUE_BACKEND_ACTION,
        ids,
        confirmDestructive: false,
      })
    },
    [bulkMutation]
  )

  const runQueueAction = useCallback(
    (action: OrganizeBulkActionId) => {
      const ids = Array.from(selected)
      if (ids.length === 0) {
        addToast({ type: 'info', title: 'Select at least one message' })
        return
      }

      const backendAction = action === 'dismiss' ? MARK_DONE_BACKEND_ACTION : action

      if (backendAction === 'archive') {
        const ok = window.confirm(
          `File away ${ids.length} message(s) in Gmail?\n\nThey leave your main inbox but stay in Gmail All Mail.`
        )
        if (!ok) return
        bulkMutation.mutate({ action: backendAction, ids, confirmDestructive: false })
        return
      }

      if (backendAction === MARK_DONE_BACKEND_ACTION) {
        lastMarkDoneIdsRef.current = [...ids]
        bulkMutation.mutate(
          { action: MARK_DONE_BACKEND_ACTION, ids, confirmDestructive: false },
          {
            onSuccess: (res) => {
              const processed = res.processed ?? ids.length
              addToast({
                type: 'success',
                title: `Marked ${processed} as done`,
                message: 'Hidden from Organize. Still in Gmail.',
                duration: MARK_DONE_UNDO_MS,
                undo: {
                  label: 'Undo',
                  onClick: () => restoreMarkDone(lastMarkDoneIdsRef.current),
                },
              })
            },
          }
        )
        return
      }

      bulkMutation.mutate({ action: backendAction, ids, confirmDestructive: false })
    },
    [addToast, bulkMutation, restoreMarkDone, selected]
  )

  const switchQueue = useCallback(
    (queue: OrganizeQueueId) => {
      setActiveQueue(queue)
      clearSelection()
      setExpandedReasonId(null)
    },
    [clearSelection]
  )

  const busy =
    isListLoading || isListFetching || bulkMutation.isPending || syncPending || syncing

  const queueActions: OrganizeQueueAction[] = QUEUE_ACTIONS[activeQueue]
  const notSureCount = categoryCounts[NOT_SURE_CATEGORY] ?? 0

  return (
    <div
      className="flex h-[calc(100dvh-11rem)] max-h-[calc(100dvh-11rem)] min-h-0 flex-col overflow-hidden rounded-lg border border-brand-text/10 bg-brand-background dark:border-gray-700 dark:bg-gray-900 lg:h-[calc(100dvh-8rem)] lg:max-h-[calc(100dvh-8rem)]"
      role="main"
      aria-label="Inbox Organize"
    >
      <div className="shrink-0 border-b border-brand-text/10 p-3 dark:border-gray-700 sm:p-4">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-bold text-brand-text dark:text-white">Organize</h2>
            <p className="text-xs text-brand-text/60 dark:text-gray-400">
              Sorted piles for your business mail. You approve every move.
            </p>
            {syncing ? (
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                Updating…
                {syncStatus?.progress != null ? ` ${syncStatus.progress}%` : ''}
              </p>
            ) : unclassifiedCount > 0 ? (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
                Sorting {unclassifiedCount} new message{unclassifiedCount === 1 ? '' : 's'}…
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => void runUpdateAndSort()}
            disabled={busy}
            className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-lg bg-brand-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-sky-600"
          >
            {syncPending || syncing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Update &amp; sort
          </button>
        </div>

        <div
          className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3"
          role="tablist"
          aria-label="Organize queues"
        >
          {ORGANIZE_QUEUES.map((queue) => {
            const count = queueCount(categoryCounts, queue)
            const selectedQueue = activeQueue === queue.id
            return (
              <button
                key={queue.id}
                type="button"
                role="tab"
                aria-selected={selectedQueue}
                onClick={() => switchQueue(queue.id)}
                className={`rounded-xl border-2 p-3 text-left transition-shadow ${
                  queue.cardClass
                } ${selectedQueue ? 'ring-2 ring-brand-primary/40 dark:ring-sky-500/50' : 'opacity-90 hover:opacity-100'}`}
              >
                <div className={`text-2xl font-bold tabular-nums ${queue.countAccentClass}`}>
                  {count}
                </div>
                <div className="mt-0.5 text-sm font-semibold text-brand-text dark:text-gray-100">
                  {queue.label}
                </div>
                <div className="text-xs text-brand-text/60 dark:text-gray-400">{queue.subtitle}</div>
              </button>
            )
          })}
        </div>

        {notSureCount > 0 ? (
          <button
            type="button"
            role="tab"
            aria-selected={activeQueue === 'not_sure'}
            onClick={() => switchQueue('not_sure')}
            className={`mb-3 inline-flex min-h-[36px] items-center rounded-full border px-3 py-1 text-xs font-medium ${
              activeQueue === 'not_sure'
                ? 'border-yellow-300 bg-yellow-50 text-yellow-950 dark:border-yellow-800 dark:bg-yellow-950/40 dark:text-yellow-100'
                : 'border-yellow-200/80 bg-yellow-50/60 text-yellow-900 hover:bg-yellow-50 dark:border-yellow-900/50 dark:bg-yellow-950/20 dark:text-yellow-200'
            }`}
          >
            Not sure ({notSureCount})
          </button>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {queueActions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => runQueueAction(action.id)}
              disabled={busy || selected.size === 0}
              className={
                action.primary
                  ? 'inline-flex min-h-[44px] items-center gap-1 rounded-lg bg-brand-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-sky-600'
                  : 'inline-flex min-h-[44px] items-center gap-1 rounded-lg border border-brand-text/15 bg-white px-3 py-2 text-sm font-medium text-brand-text disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200'
              }
            >
              {action.id === 'archive' ? (
                <Archive className="h-4 w-4" />
              ) : action.id === 'create_leads' ? (
                <Sparkles className="h-4 w-4" />
              ) : null}
              {action.label}
              {selected.size > 0 ? ` (${selected.size})` : ''}
            </button>
          ))}
          <button
            type="button"
            onClick={selectAllVisible}
            disabled={emails.length === 0}
            className="text-xs text-brand-text/70 hover:text-brand-primary dark:text-gray-400 dark:hover:text-sky-400"
          >
            Select all
          </button>
          {selected.size > 0 ? (
            <button type="button" onClick={clearSelection} className="text-xs text-brand-text/50">
              Clear
            </button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isListLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
          </div>
        ) : emails.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title={syncing ? 'Updating your inbox' : `Nothing in ${queueLabel}`}
            description={
              syncing
                ? 'Your piles will refresh in a moment.'
                : organizeAttentionCount(categoryCounts) === 0
                  ? 'Tap Update & sort to pull in mail and sort it into piles.'
                  : `Nothing here right now. Check another pile or tap Update & sort.`
            }
          />
        ) : (
          <ul className="divide-y divide-gray-200/80 dark:divide-gray-700/80">
            {emails.map((email) => {
              const checked = selected.has(email.id)
              const tag = humanPriorityTag(email, activeQueue)
              const showReason = expandedReasonId === email.id
              return (
                <li
                  key={email.id}
                  className={`flex gap-3 px-3 py-3 sm:px-4 ${checked ? 'bg-slate-50/90 dark:bg-slate-800/50' : ''}`}
                >
                  <input
                    id={`email-organize-select-${email.id}`}
                    name="selected_email_ids"
                    type="checkbox"
                    className="mt-1 h-5 w-5 shrink-0 rounded border-gray-300"
                    checked={checked}
                    onChange={() => toggleSelect(email.id)}
                    aria-label={`Select ${email.subject}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium text-brand-text dark:text-gray-100">
                        {email.from || 'Unknown sender'}
                      </span>
                      {tag ? (
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium leading-none ${priorityTagClass(tag)}`}
                        >
                          {tag}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-sm font-semibold text-brand-text dark:text-gray-200">
                      {email.subject}
                    </p>
                    {email.reason ? (
                      <div className="mt-1">
                        <button
                          type="button"
                          className="text-xs text-brand-text/50 hover:text-brand-primary dark:text-gray-500 dark:hover:text-sky-400"
                          onClick={() =>
                            setExpandedReasonId(showReason ? null : email.id)
                          }
                          aria-expanded={showReason}
                        >
                          {showReason ? 'Hide note' : 'Why?'}
                        </button>
                        {showReason ? (
                          <p className="mt-0.5 line-clamp-3 text-xs text-brand-text/70 dark:text-gray-500">
                            {email.reason}
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <footer className="shrink-0 border-t border-brand-text/10 bg-slate-50/90 px-4 py-3 dark:border-gray-700 dark:bg-slate-900/50">
        <ul className="space-y-0.5 text-xs text-brand-text/60 dark:text-gray-400">
          {ORGANIZE_TRUST_LINES.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </footer>
    </div>
  )
}
