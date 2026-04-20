/**
 * Canonical payload shape for the "Capture leads from email" (gmail_crm) preset.
 * Keep in sync with services/automation_engine expectations and Automations.tsx.
 */

export const GMAIL_CRM_PRESET_ID = 'gmail_crm' as const

export type GmailCrmSetupOptions = {
  /** CRM pipeline stage for new/updated leads from inbound mail */
  targetStage: string
  /**
   * Optional: only run when sender address ends with this string (e.g. "@acme.com" or "acme.com").
   * Stored as trigger_conditions.if with sender_email + ends_with.
   */
  senderEmailEndsWith?: string
}

export function buildGmailCrmTriggerConditions(opts: GmailCrmSetupOptions): Record<string, unknown> {
  const out: Record<string, unknown> = { slug: GMAIL_CRM_PRESET_ID }
  const raw = opts.senderEmailEndsWith?.trim()
  if (!raw) return out
  out.if = {
    match: 'all',
    conditions: [{ field: 'sender_email', op: 'ends_with', value: raw }],
  }
  return out
}

export function buildGmailCrmActionParameters(opts: GmailCrmSetupOptions): Record<string, unknown> {
  return {
    target_stage: opts.targetStage,
    tags: ['inbox'],
    slug: GMAIL_CRM_PRESET_ID,
  }
}
