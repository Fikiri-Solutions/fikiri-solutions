import React from 'react'

/** Optional local overlay fields from GET /api/email/messages */
export interface LiveMailLocalOverlay {
  classification_category?: string
  classification_confidence?: number
  lead_score?: number
  urgency_score?: number
  workflow_status?: string
  classification_status?: string
  last_action?: string
  handled_at?: string
  is_locally_archived?: boolean
  is_locally_handled?: boolean
}

/** Calm Read-tab labels — one badge max, no scores or jargon */
const CATEGORY_LABELS: Record<string, string> = {
  business_lead: 'Opportunity',
  action_needed: 'Needs reply',
  existing_client: 'Client',
  newsletter_marketing: 'Newsletter',
  newsletter: 'Newsletter',
  personal_non_business: 'Personal',
  vendor_partner: 'Vendor',
  spam_risk: 'Junk',
  review_needed: 'Not sure',
}

const WORKFLOW_LABELS: Record<string, string> = {
  archived: 'Filed in Gmail',
  dismissed: 'Done',
  done: 'Done',
  converted_to_lead: 'Saved',
  replied: 'Replied',
}

type BadgeTone = 'lead' | 'action' | 'handled' | 'muted' | 'unsure'

function badgeClass(tone: BadgeTone): string {
  const base =
    'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium leading-none'
  switch (tone) {
    case 'lead':
      return `${base} bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300`
    case 'action':
      return `${base} bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200`
    case 'unsure':
      return `${base} bg-yellow-100 text-yellow-900 dark:bg-yellow-950/40 dark:text-yellow-200`
    case 'handled':
      return `${base} bg-slate-200/90 text-slate-600 dark:bg-slate-700/80 dark:text-slate-400`
    default:
      return `${base} bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400`
  }
}

function pickSingleBadge(email: LiveMailLocalOverlay): {
  key: string
  label: string
  tone: BadgeTone
} | null {
  const ws = (email.workflow_status || '').trim().toLowerCase()
  if (ws && ws !== 'active') {
    const wfLabel = WORKFLOW_LABELS[ws]
    if (wfLabel) {
      return {
        key: `wf-${ws}`,
        label: wfLabel,
        tone: 'handled',
      }
    }
  }
  if (email.is_locally_archived) {
    return { key: 'archived', label: 'Filed in Gmail', tone: 'handled' }
  }
  if (email.is_locally_handled) {
    return { key: 'handled', label: 'Done', tone: 'handled' }
  }

  const category = email.classification_category?.trim()
  if (!category) return null

  if (category === 'business_lead') {
    return { key: `cat-${category}`, label: 'Opportunity', tone: 'lead' }
  }
  if (category === 'action_needed') {
    return { key: `cat-${category}`, label: 'Needs reply', tone: 'action' }
  }
  if (category === 'review_needed') {
    return { key: `cat-${category}`, label: 'Not sure', tone: 'unsure' }
  }
  const label = CATEGORY_LABELS[category]
  if (!label) return null
  return { key: `cat-${category}`, label, tone: 'muted' }
}

/** At most one calm badge on Live Mail rows (Organize state hint). */
export function LiveMailLocalBadges({ email }: { email: LiveMailLocalOverlay }) {
  const badge = pickSingleBadge(email)
  if (!badge) return null

  return (
    <div className="mt-1" aria-label="Inbox hint">
      <span className={badgeClass(badge.tone)}>{badge.label}</span>
    </div>
  )
}
