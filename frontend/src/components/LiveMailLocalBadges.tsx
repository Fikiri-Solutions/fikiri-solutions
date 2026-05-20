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

const CATEGORY_LABELS: Record<string, string> = {
  business_lead: 'Lead',
  action_needed: 'Action Needed',
  newsletter: 'Newsletter',
  promotional: 'Promo',
  automated_notification: 'Automated',
  personal_non_business: 'Personal',
  vendor_partner: 'Vendor',
  existing_client: 'Client',
  spam_risk: 'Spam/Risk',
  review_needed: 'Review',
}

const WORKFLOW_LABELS: Record<string, string> = {
  archived: 'Archived locally',
  dismissed: 'Dismissed',
  done: 'Done',
  spam: 'Spam/Risk',
  converted_to_lead: 'Converted',
  replied: 'Replied',
}

type BadgeTone = 'neutral' | 'lead' | 'action' | 'handled' | 'muted'

function badgeClass(tone: BadgeTone): string {
  const base =
    'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium leading-none'
  switch (tone) {
    case 'lead':
      return `${base} bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300`
    case 'action':
      return `${base} bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200`
    case 'handled':
      return `${base} bg-slate-200/90 text-slate-700 dark:bg-slate-700/80 dark:text-slate-300`
    default:
      return `${base} bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400`
  }
}

function categoryTone(category: string): BadgeTone {
  if (category === 'business_lead') return 'lead'
  if (category === 'action_needed' || category === 'spam_risk') return 'action'
  return 'muted'
}

/** Small read-only badges for Command Center / workflow state on Live Mail rows. */
export function LiveMailLocalBadges({ email }: { email: LiveMailLocalOverlay }) {
  const badges: { key: string; label: string; tone: BadgeTone }[] = []

  const category = email.classification_category?.trim()
  if (category) {
    badges.push({
      key: `cat-${category}`,
      label: CATEGORY_LABELS[category] ?? 'Classified',
      tone: categoryTone(category),
    })
  } else if (email.classification_status === 'classified' || email.classification_status === 'reclassified') {
    badges.push({ key: 'classified', label: 'Classified', tone: 'neutral' })
  }

  const ws = (email.workflow_status || '').trim().toLowerCase()
  if (ws && ws !== 'active') {
    const wfLabel = WORKFLOW_LABELS[ws]
    if (wfLabel) {
      badges.push({
        key: `wf-${ws}`,
        label: wfLabel,
        tone: ws === 'archived' || ws === 'dismissed' || ws === 'done' ? 'handled' : 'muted',
      })
    }
  } else if (email.is_locally_archived) {
    badges.push({ key: 'archived', label: 'Archived locally', tone: 'handled' })
  }

  if (
    email.is_locally_handled &&
    !badges.some((b) => b.label === 'Archived locally' || b.label === 'Dismissed' || b.label === 'Done')
  ) {
    badges.push({ key: 'handled', label: 'Handled', tone: 'handled' })
  }

  if (badges.length === 0) {
    return null
  }

  return (
    <div className="mt-1 flex flex-wrap gap-1" aria-label="Local inbox state">
      {badges.map((b) => (
        <span key={b.key} className={badgeClass(b.tone)}>
          {b.label}
        </span>
      ))}
    </div>
  )
}
