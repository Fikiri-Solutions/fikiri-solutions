/**
 * Simple-first Inbox UX: calm labels and queue groupings.
 * Backend category IDs are unchanged; this file is presentation-only.
 */

import type { TriageCategoryId } from './emailCommandCenterTabs'

export type OrganizeQueueId = 'opportunities' | 'needs_reply' | 'clear_out' | 'not_sure'

export interface OrganizeQueueDef {
  id: OrganizeQueueId
  label: string
  subtitle: string
  categories: TriageCategoryId[]
  cardClass: string
  countAccentClass: string
}

export const ORGANIZE_QUEUES: OrganizeQueueDef[] = [
  {
    id: 'opportunities',
    label: 'Opportunities',
    subtitle: 'New business waiting',
    categories: ['business_lead'],
    cardClass:
      'border-emerald-200 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-950/30',
    countAccentClass: 'text-emerald-800 dark:text-emerald-300',
  },
  {
    id: 'needs_reply',
    label: 'Needs reply',
    subtitle: 'People waiting on you',
    categories: ['action_needed', 'existing_client'],
    cardClass: 'border-amber-200 bg-amber-50/80 dark:border-amber-900/60 dark:bg-amber-950/30',
    countAccentClass: 'text-amber-900 dark:text-amber-200',
  },
  {
    id: 'clear_out',
    label: 'Clear out',
    subtitle: 'Safe to tidy in bulk',
    categories: [
      'newsletter_marketing',
      'personal_non_business',
      'spam_risk',
      'vendor_partner',
    ],
    cardClass: 'border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/40',
    countAccentClass: 'text-slate-700 dark:text-slate-300',
  },
]

export const NOT_SURE_CATEGORY: TriageCategoryId = 'review_needed'

/** Maps backend dismiss action — UI says Mark done */
export const MARK_DONE_BACKEND_ACTION = 'dismiss'

/** Restores Mark done / dismiss — returns row to Organize queue */
export const RESTORE_TO_QUEUE_BACKEND_ACTION = 'restore_to_queue'

export const MARK_DONE_UNDO_MS = 8000

export const ORGANIZE_TRUST_LINES = [
  'Fikiri organizes your inbox. You stay in control.',
  'Nothing leaves Gmail without your approval.',
  'Filed mail stays in Gmail All Mail.',
] as const

export function queueCount(
  counts: Record<string, number> | undefined,
  queue: OrganizeQueueDef
): number {
  if (!counts) return 0
  return queue.categories.reduce((sum, cat) => sum + (counts[cat] ?? 0), 0)
}

export function organizeAttentionCount(counts: Record<string, number> | undefined): number {
  const primary = ORGANIZE_QUEUES.reduce((sum, q) => sum + queueCount(counts, q), 0)
  const unsure = counts?.[NOT_SURE_CATEGORY] ?? 0
  return primary + unsure
}

export interface TriageRowSignals {
  lead_score: number
  urgency_score: number
  confidence: number
  category: string
}

/** One calm tag for list rows — no raw scores in simple mode */
export function humanPriorityTag(
  row: TriageRowSignals,
  queue: OrganizeQueueId
): string | null {
  if (queue === 'not_sure' || row.category === NOT_SURE_CATEGORY) {
    return 'Not sure'
  }
  if (row.confidence > 0 && row.confidence < 0.55) {
    return 'Not sure'
  }
  if (row.lead_score >= 65) {
    return 'Strong lead'
  }
  if (row.urgency_score >= 55) {
    return 'Reply today'
  }
  if (row.lead_score >= 40 || row.urgency_score >= 35) {
    return 'Can wait'
  }
  return null
}

export function priorityTagClass(tag: string): string {
  if (tag === 'Strong lead') {
    return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
  }
  if (tag === 'Reply today') {
    return 'bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200'
  }
  if (tag === 'Not sure') {
    return 'bg-yellow-100 text-yellow-900 dark:bg-yellow-950/40 dark:text-yellow-200'
  }
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
}

export function primaryCategoryForQueue(queue: OrganizeQueueId): TriageCategoryId {
  const def = ORGANIZE_QUEUES.find((q) => q.id === queue)
  return def?.categories[0] ?? 'business_lead'
}
