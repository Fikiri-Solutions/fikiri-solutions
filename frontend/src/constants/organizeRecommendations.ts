/**
 * Organize presentation helpers — maps backend triage fields to user-safe copy.
 * Does not classify mail; only translates existing cleanup_action / reason values.
 */

import type { OrganizeQueueId } from './inboxSimpleFirst'
import { NOT_SURE_CATEGORY } from './inboxSimpleFirst'

export type BackendCleanupAction =
  | 'keep'
  | 'archive'
  | 'label'
  | 'delete_candidate'
  | 'spam_candidate'
  | string

export type RecommendationBulkAction = 'archive' | 'spam_candidate' | 'delete_candidate' | 'label'

export interface OrganizeEmailSignals {
  id: string
  cleanup_action: string
  suggested_labels?: string[]
  category?: string
  reason?: string
}

export interface RecommendationGroup {
  bulkAction: RecommendationBulkAction
  userLabel: string
  emailIds: string[]
  destructive: boolean
  labelNames?: string[]
}

const DESTRUCTIVE_BULK = new Set<RecommendationBulkAction>(['spam_candidate', 'delete_candidate'])

export function normalizeCleanupAction(raw: string | undefined): BackendCleanupAction {
  const key = String(raw ?? 'keep').trim().toLowerCase()
  if (key === 'spam' || key === 'report_spam') return 'spam_candidate'
  if (key === 'delete' || key === 'trash') return 'delete_candidate'
  return key as BackendCleanupAction
}

/** Backend bulk-action id for a stored cleanup_action (null = no Gmail bulk step). */
export function cleanupToBulkAction(cleanup: string | undefined): RecommendationBulkAction | null {
  const key = normalizeCleanupAction(cleanup)
  if (key === 'archive') return 'archive'
  if (key === 'spam_candidate') return 'spam_candidate'
  if (key === 'delete_candidate') return 'delete_candidate'
  if (key === 'label') return 'label'
  return null
}

/** User-facing label for a cleanup recommendation (never expose raw cleanup_action). */
export function cleanupActionUserLabel(cleanup: string | undefined): string {
  const key = normalizeCleanupAction(cleanup)
  switch (key) {
    case 'archive':
      return 'File away in Gmail'
    case 'spam_candidate':
      return 'Report spam'
    case 'delete_candidate':
      return 'Move to trash'
    case 'label':
      return 'Apply label'
    case 'keep':
      return 'Leave in inbox'
    default:
      return 'Needs review'
  }
}

export function isDestructiveBulkAction(action: RecommendationBulkAction): boolean {
  return DESTRUCTIVE_BULK.has(action)
}

/** Group selected rows by recommended bulk action (and label set when action is label). */
export function buildRecommendationGroups(
  emails: OrganizeEmailSignals[],
  options?: { safeOnly?: boolean }
): RecommendationGroup[] {
  const safeOnly = options?.safeOnly === true
  const buckets = new Map<string, RecommendationGroup>()

  for (const row of emails) {
    const bulk = cleanupToBulkAction(row.cleanup_action)
    if (!bulk) continue
    if (safeOnly && isDestructiveBulkAction(bulk)) continue

    const labelNames =
      bulk === 'label'
        ? (row.suggested_labels ?? []).filter((n) => typeof n === 'string' && n.trim())
        : undefined
    if (bulk === 'label' && (!labelNames || labelNames.length === 0)) continue

    const bucketKey =
      bulk === 'label' ? `label:${labelNames!.join('\u0001')}` : bulk
    const existing = buckets.get(bucketKey)
    if (existing) {
      existing.emailIds.push(row.id)
      continue
    }
    buckets.set(bucketKey, {
      bulkAction: bulk,
      userLabel: cleanupActionUserLabel(row.cleanup_action),
      emailIds: [row.id],
      destructive: isDestructiveBulkAction(bulk),
      labelNames: bulk === 'label' ? labelNames : undefined,
    })
  }

  const order: RecommendationBulkAction[] = [
    'archive',
    'label',
    'spam_candidate',
    'delete_candidate',
  ]
  return order
    .map((action) => Array.from(buckets.values()).filter((g) => g.bulkAction === action))
    .flat()
}

export function countActionableRecommendations(
  emails: OrganizeEmailSignals[],
  options?: { safeOnly?: boolean }
): number {
  return buildRecommendationGroups(emails, options).reduce((sum, g) => sum + g.emailIds.length, 0)
}

export function formatRecommendationSummary(groups: RecommendationGroup[]): string {
  if (groups.length === 0) return 'No recommendations to apply for the current selection.'
  return groups
    .map((g) => `${g.userLabel}: ${g.emailIds.length} message${g.emailIds.length === 1 ? '' : 's'}`)
    .join('\n')
}

const REASON_REPLACEMENTS: Array<[RegExp, string]> = [
  [/heuristic classification.*ai unavailable/i, 'We were not sure, so we kept it for review.'],
  [/ai unavailable/i, 'We kept this for your review.'],
  [/newsletter\/?marketing/i, 'This looks promotional and may be safe to file away.'],
  [/spam|risk|scam/i, 'This looks like junk mail.'],
  [/unsubscribe/i, 'This looks like a mailing list or promotion.'],
  [/possible lead|pricing|quote|consultation/i, 'This may be a customer asking about your services.'],
  [/action needed|reply|waiting/i, 'Someone may be waiting for a reply from you.'],
  [/no strong rule match/i, 'We were not sure, so we kept it for review.'],
]

function categoryFallbackReason(category: string, cleanup: string, queue: OrganizeQueueId): string {
  const cat = category.trim().toLowerCase()
  const cleanupLabel = cleanupActionUserLabel(cleanup)
  if (queue === 'not_sure' || cat === NOT_SURE_CATEGORY) {
    return 'We were not sure, so we kept it for review.'
  }
  if (cat === 'business_lead') {
    return 'This may be a new business opportunity based on what they wrote.'
  }
  if (cat === 'action_needed' || cat === 'existing_client') {
    return 'This asks for attention, so we placed it in Needs reply.'
  }
  if (
    cat === 'newsletter_marketing' ||
    cat === 'personal_non_business' ||
    cat === 'spam_risk' ||
    cat === 'vendor_partner'
  ) {
    return `This looks like mail you can tidy. Suggested next step: ${cleanupLabel}.`
  }
  if (normalizeCleanupAction(cleanup) !== 'keep') {
    return `Suggested next step: ${cleanupLabel}.`
  }
  return 'Sorted into this pile based on the subject and sender.'
}

/** Plain-language note for Why? — strips internal jargon when possible. */
export function displayOrganizeReason(
  row: { reason?: string; category?: string; cleanup_action?: string },
  queue: OrganizeQueueId
): string {
  const raw = String(row.reason ?? '').trim()
  if (raw) {
    for (const [pattern, replacement] of REASON_REPLACEMENTS) {
      if (pattern.test(raw)) return replacement
    }
    const lower = raw.toLowerCase()
    if (
      !lower.includes('cleanup_action') &&
      !lower.includes('spam_candidate') &&
      !lower.includes('delete_candidate') &&
      !lower.includes('heuristic') &&
      !lower.includes('taxonomy') &&
      !lower.includes('confidence')
    ) {
      return raw.length > 280 ? `${raw.slice(0, 277)}…` : raw
    }
  }
  return categoryFallbackReason(
    String(row.category ?? ''),
    String(row.cleanup_action ?? 'keep'),
    queue
  )
}

export function suggestedNextStepLine(cleanup: string | undefined): string | null {
  const key = normalizeCleanupAction(cleanup)
  if (key === 'keep') return null
  return `Suggested: ${cleanupActionUserLabel(cleanup)}`
}
