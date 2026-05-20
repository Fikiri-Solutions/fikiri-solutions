import React, { useCallback, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, Loader2, RefreshCw, ShieldAlert, Tag } from 'lucide-react'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { EmptyState } from '../components/EmptyState'
import {
  DESTRUCTIVE_TRIAGE_ACTIONS,
  EMAIL_COMMAND_CENTER_TABS,
  type TriageCategoryId,
} from '../constants/emailCommandCenterTabs'

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

const BULK_ACTIONS = [
  { id: 'archive', label: 'Archive' },
  { id: 'mark_read', label: 'Mark read' },
  { id: 'mark_unread', label: 'Mark unread' },
  { id: 'label', label: 'Add Gmail label' },
  { id: 'create_leads', label: 'Create leads' },
  { id: 'delete_candidate', label: 'Delete (review)' },
  { id: 'spam_candidate', label: 'Move to spam (review)' },
] as const

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

export const EmailCommandCenter: React.FC = () => {
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const [category, setCategory] = useState<TriageCategoryId>('business_lead')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulkAction, setBulkAction] = useState<string>('archive')

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['email-triage', category],
    queryFn: () => apiClient.getEmailTriage({ category, limit: 20 }),
    staleTime: 60_000,
  })

  const emails = useMemo(() => {
    const rows = (data?.emails ?? []) as Record<string, unknown>[]
    return rows.map(normalizeRow).filter((r): r is TriageListEmail => r != null)
  }, [data])

  const tabLabel =
    EMAIL_COMMAND_CENTER_TABS.find((t) => t.id === category)?.label ?? category

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

  const classifyMutation = useMutation({
    mutationFn: (ids: string[]) => apiClient.classifyEmailTriage(ids),
    onSuccess: (res) => {
      addToast({
        type: 'success',
        title: 'Classification updated',
        message: `${res.count ?? 0} message(s) classified.`,
      })
      queryClient.invalidateQueries({ queryKey: ['email-triage'] })
      refetch()
    },
    onError: () => {
      addToast({ type: 'error', title: 'Classification failed' })
    },
  })

  const bulkMutation = useMutation({
    mutationFn: async (opts: {
      action: string
      ids: string[]
      confirmDestructive: boolean
      labelNames?: string[]
    }) =>
      apiClient.emailTriageBulkAction({
        action: opts.action,
        email_ids: opts.ids,
        confirm_destructive: opts.confirmDestructive,
        label_names: opts.labelNames,
      }),
    onSuccess: (res, vars) => {
      addToast({
        type: 'success',
        title: 'Bulk action complete',
        message: `Processed ${res.processed ?? 0} email(s).`,
      })
      clearSelection()
      queryClient.invalidateQueries({ queryKey: ['email-triage'] })
      refetch()
    },
    onError: () => {
      addToast({ type: 'error', title: 'Bulk action failed' })
    },
  })

  const runBulkAction = useCallback(() => {
    const ids = Array.from(selected)
    if (ids.length === 0) {
      addToast({ type: 'info', title: 'Select at least one email' })
      return
    }

    let confirmDestructive = false
    if (DESTRUCTIVE_TRIAGE_ACTIONS.has(bulkAction)) {
      const label =
        bulkAction === 'spam_candidate' ? 'move to spam' : 'delete (trash)'
      const ok = window.confirm(
        `Apply "${label}" to ${ids.length} selected email(s)? This uses Gmail and cannot be undone from Fikiri alone.`
      )
      if (!ok) return
      confirmDestructive = true
    }

    let labelNames: string[] | undefined
    if (bulkAction === 'label') {
      const raw = window.prompt('Gmail label name(s), comma-separated:', 'Fikiri/review')
      if (!raw?.trim()) return
      labelNames = raw.split(',').map((s) => s.trim()).filter(Boolean)
    }

    bulkMutation.mutate({
      action: bulkAction,
      ids,
      confirmDestructive,
      labelNames,
    })
  }, [selected, bulkAction, bulkMutation, addToast])

  const busy = isLoading || isFetching || bulkMutation.isPending || classifyMutation.isPending

  return (
    <div
      className="flex h-[calc(100dvh-11rem)] max-h-[calc(100dvh-11rem)] min-h-0 flex-col overflow-hidden rounded-lg border border-brand-text/10 bg-brand-background dark:border-gray-700 dark:bg-gray-900 lg:h-[calc(100dvh-8rem)] lg:max-h-[calc(100dvh-8rem)]"
      role="main"
      aria-label="Inbox Command Center"
    >
      <div className="shrink-0 border-b border-brand-text/10 p-3 dark:border-gray-700 sm:p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-brand-text dark:text-white">Command Center</h2>
            <p className="text-xs text-brand-text/60 dark:text-gray-400">
              Organize synced mail by AI triage. Nothing is deleted without your confirmation.
            </p>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={busy}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-brand-text/70 hover:bg-gray-50 disabled:opacity-50 dark:hover:bg-gray-800"
            aria-label="Refresh triage list"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div
          className="mb-3 flex gap-1 overflow-x-auto pb-1"
          role="tablist"
          aria-label="Triage categories"
        >
          {EMAIL_COMMAND_CENTER_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={category === tab.id}
              onClick={() => {
                setCategory(tab.id)
                clearSelection()
              }}
              className={`shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-medium sm:text-sm ${
                category === tab.id
                  ? 'bg-brand-primary text-white dark:bg-sky-600'
                  : 'bg-gray-100 text-brand-text/80 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={bulkAction}
            onChange={(e) => setBulkAction(e.target.value)}
            className="min-h-[44px] rounded-lg border border-brand-text/15 bg-white px-2 text-sm dark:border-gray-600 dark:bg-gray-900"
            aria-label="Bulk action"
          >
            {BULK_ACTIONS.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={runBulkAction}
            disabled={busy || selected.size === 0}
            className="inline-flex min-h-[44px] items-center gap-1 rounded-lg bg-brand-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-sky-600"
          >
            {bulkMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Archive className="h-4 w-4" />
            )}
            Apply ({selected.size})
          </button>
          <button
            type="button"
            onClick={() => classifyMutation.mutate(Array.from(selected))}
            disabled={busy || selected.size === 0}
            className="inline-flex min-h-[44px] items-center gap-1 rounded-lg border border-brand-text/15 px-3 py-2 text-sm dark:border-gray-600"
          >
            <Tag className="h-4 w-4" />
            Re-classify
          </button>
          <button
            type="button"
            onClick={selectAllVisible}
            disabled={emails.length === 0}
            className="text-xs text-brand-primary dark:text-sky-400"
          >
            Select all
          </button>
          {selected.size > 0 ? (
            <button type="button" onClick={clearSelection} className="text-xs text-brand-text/60">
              Clear
            </button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
          </div>
        ) : emails.length === 0 ? (
          <EmptyState
            icon={ShieldAlert}
            title={`No emails in ${tabLabel}`}
            description="Run Gmail sync from Live mail, then re-classify messages here. Classifications appear after sync and triage."
          />
        ) : (
          <ul className="divide-y divide-gray-200/80 dark:divide-gray-700/80">
            {emails.map((email) => {
              const checked = selected.has(email.id)
              return (
                <li
                  key={email.id}
                  className={`flex gap-3 px-3 py-3 sm:px-4 ${checked ? 'bg-sky-50/80 dark:bg-sky-950/30' : ''}`}
                >
                  <input
                    type="checkbox"
                    className="mt-1 h-5 w-5 shrink-0 rounded border-gray-300"
                    checked={checked}
                    onChange={() => toggleSelect(email.id)}
                    aria-label={`Select ${email.subject}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="truncate text-sm font-medium text-brand-text dark:text-gray-100">
                        {email.from || 'Unknown sender'}
                      </span>
                      <span className="text-xs tabular-nums text-gray-500">
                        Lead {email.lead_score} · Urgency {email.urgency_score}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm font-semibold text-brand-text dark:text-gray-200">
                      {email.subject}
                    </p>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-medium">{email.cleanup_action}</span>
                      {' · '}
                      confidence {(email.confidence * 100).toFixed(0)}%
                      {' · '}
                      {email.category}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-brand-text/70 dark:text-gray-500">
                      {email.reason}
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {DESTRUCTIVE_TRIAGE_ACTIONS.has(bulkAction) ? (
        <p className="shrink-0 border-t border-amber-200/80 bg-amber-50/90 px-4 py-2 text-xs text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
          Delete and spam actions require confirmation and only run when you click Apply.
        </p>
      ) : null}
    </div>
  )
}
