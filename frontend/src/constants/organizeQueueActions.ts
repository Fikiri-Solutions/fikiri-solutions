/**
 * Queue-specific Organize action strips (presentation only).
 * Backend action ids are mapped in EmailCommandCenter when executing.
 */

import type { OrganizeQueueId } from './inboxSimpleFirst'

export type OrganizeUiActionId =
  | 'create_leads'
  | 'open_read'
  | 'dismiss'
  | 'archive'
  | 'apply_recommendations'
  | 'spam_candidate'
  | 'delete_candidate'
  | 'move_clear_out'

export interface OrganizeQueueActionDef {
  id: OrganizeUiActionId
  label: string
  primary?: boolean
  outline?: boolean
  /** Destructive Gmail actions — visually de-emphasized */
  guarded?: boolean
}

export const ORGANIZE_QUEUE_ACTIONS: Record<OrganizeQueueId, OrganizeQueueActionDef[]> = {
  opportunities: [
    { id: 'create_leads', label: 'Save lead', primary: true },
    { id: 'open_read', label: 'Open', primary: true },
    { id: 'dismiss', label: 'Mark done', outline: true },
  ],
  needs_reply: [
    { id: 'open_read', label: 'Open', primary: true },
    { id: 'dismiss', label: 'Mark done', primary: true },
    { id: 'archive', label: 'File away in Gmail', outline: true },
  ],
  clear_out: [
    { id: 'archive', label: 'File away in Gmail', primary: true },
    { id: 'apply_recommendations', label: 'Apply recommendations', primary: true },
    { id: 'dismiss', label: 'Mark done', outline: true },
    { id: 'spam_candidate', label: 'Report spam', guarded: true },
    { id: 'delete_candidate', label: 'Move to trash', guarded: true },
  ],
  not_sure: [
    { id: 'open_read', label: 'Review', primary: true },
    { id: 'apply_recommendations', label: 'Apply safe cleanup', primary: true },
    { id: 'move_clear_out', label: 'Move to Clear out', outline: true },
    { id: 'dismiss', label: 'Mark done', outline: true },
  ],
}
