/**
 * Canonical preset slug for inbound email → CRM merge (legacy slug still accepted by API/engine: gmail_crm).
 */

export const INBOUND_CRM_SYNC_PRESET_ID = 'inbound_crm_sync' as const

const LEGACY_INBOUND_CRM_PRESET_SLUG = 'gmail_crm' as const

/** True if rule parameters use the current or legacy inbound CRM sync preset slug. */
export function isInboundCrmSyncSlug(slug: unknown): boolean {
  return slug === INBOUND_CRM_SYNC_PRESET_ID || slug === LEGACY_INBOUND_CRM_PRESET_SLUG
}

export type InboundCrmSyncSetupOptions = {
  /** CRM pipeline stage for new/updated leads from inbound mail */
  targetStage: string
  /**
   * Optional: only run when sender address ends with this string (e.g. "@acme.com" or "acme.com").
   * Stored as trigger_conditions.if with sender_email + ends_with.
   */
  senderEmailEndsWith?: string
}

export function buildInboundCrmSyncTriggerConditions(
  opts: InboundCrmSyncSetupOptions
): Record<string, unknown> {
  const out: Record<string, unknown> = { slug: INBOUND_CRM_SYNC_PRESET_ID }
  const raw = opts.senderEmailEndsWith?.trim()
  if (!raw) return out
  out.if = {
    match: 'all',
    conditions: [{ field: 'sender_email', op: 'ends_with', value: raw }],
  }
  return out
}

export function buildInboundCrmSyncActionParameters(
  opts: InboundCrmSyncSetupOptions
): Record<string, unknown> {
  return {
    target_stage: opts.targetStage,
    tags: ['inbox'],
    slug: INBOUND_CRM_SYNC_PRESET_ID,
  }
}
