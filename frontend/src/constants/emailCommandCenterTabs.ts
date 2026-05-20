/** Inbox Command Center tabs (matches backend triage categories). */

export type TriageCategoryId =
  | 'business_lead'
  | 'action_needed'
  | 'existing_client'
  | 'newsletter_marketing'
  | 'spam_risk'
  | 'personal_non_business'
  | 'review_needed'

export const EMAIL_COMMAND_CENTER_TABS: { id: TriageCategoryId; label: string }[] = [
  { id: 'business_lead', label: 'Leads' },
  { id: 'action_needed', label: 'Action Needed' },
  { id: 'existing_client', label: 'Clients' },
  { id: 'newsletter_marketing', label: 'Marketing/Newsletters' },
  { id: 'spam_risk', label: 'Spam/Risk' },
  { id: 'personal_non_business', label: 'Personal/Non-Business' },
  { id: 'review_needed', label: 'Review Queue' },
]

export const DESTRUCTIVE_TRIAGE_ACTIONS = new Set(['delete_candidate', 'spam_candidate'])
