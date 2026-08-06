/**
 * Frontend allowlist for admin audit detail + copy.
 * Backend remains authoritative for redaction; this is defense-in-depth.
 */
import type { AdminAuditEntry } from '../../types/admin'

export const REASON_CODE_RE = /^[A-Z][A-Z0-9_]{2,63}$/

/** Scalar keys allowed when summarizing before/after objects. */
const SAFE_SUMMARY_SCALAR_KEYS = new Set([
  'status',
  'outcome',
  'reason',
  'error_code',
  'code',
  'job_id',
  'tenant_id',
  'user_id',
  'target_user_id',
  'actor_user_id',
  'enrolled',
  'capability',
  'action',
  'active',
])

export type AuditDetailField = {
  key: string
  label: string
  value: string
}

export type AuditCopySummary = {
  timestamp?: string
  action?: string
  outcome?: string
  reason?: string
  actor_id?: number
  target_type?: string
  target_id?: string
  correlation_id?: string
  capability?: string
}

export function controlledReasonCode(entry: AdminAuditEntry): string | null {
  const meta = entry.metadata
  if (!meta || typeof meta !== 'object') return null
  const raw = meta.reason || meta.error_code || meta.code
  if (!raw) return null
  const code = String(raw).trim()
  if (!REASON_CODE_RE.test(code)) return null
  return code
}

export function abbreviateCorrelation(value?: string | null): string {
  if (!value) return '—'
  const text = String(value).trim()
  if (!text) return '—'
  return text.length <= 12 ? text : `${text.slice(0, 12)}…`
}

export function targetLabel(entry: AdminAuditEntry): string {
  if (entry.target_type && entry.target_id != null && entry.target_id !== '') {
    return `${entry.target_type}:${entry.target_id}`
  }
  return '—'
}

function scalarToDisplay(value: unknown): string | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    const t = value.trim()
    return t ? t : null
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return null
}

/** Allowlisted scalar pairs only — never dumps arbitrary objects. */
export function summarizeSafeObject(value: unknown): Record<string, string> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const out: Record<string, string> = {}
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (!SAFE_SUMMARY_SCALAR_KEYS.has(key)) continue
    const display = scalarToDisplay(item)
    if (display == null) continue
    // Controlled reason-like fields must match code shape when named reason/code/error_code
    if ((key === 'reason' || key === 'error_code' || key === 'code') && !REASON_CODE_RE.test(display)) {
      continue
    }
    out[key] = display
  }
  return Object.keys(out).length ? out : null
}

function formatSummaryMap(map: Record<string, string> | null): string | null {
  if (!map) return null
  return Object.entries(map)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

/** Explicit detail fields for drawer rendering (omit empties). */
export function buildAuditDetailFields(entry: AdminAuditEntry): AuditDetailField[] {
  const fields: AuditDetailField[] = []
  const push = (key: string, label: string, value: string | null | undefined) => {
    if (value == null || value === '') return
    fields.push({ key, label, value })
  }

  push('created_at', 'Timestamp', entry.created_at ? String(entry.created_at) : null)
  push('action', 'Action', entry.action ? String(entry.action) : null)
  push('outcome', 'Outcome', entry.outcome ? String(entry.outcome) : null)
  push('reason', 'Reason', controlledReasonCode(entry))
  push('capability', 'Capability', entry.capability ? String(entry.capability) : null)
  push(
    'actor',
    'Actor',
    entry.actor_user_id != null ? `user:${entry.actor_user_id}` : null,
  )
  push(
    'target',
    'Target',
    entry.target_type || entry.target_id != null
      ? targetLabel(entry) === '—'
        ? null
        : targetLabel(entry)
      : null,
  )
  push(
    'correlation_id',
    'Correlation ID',
    entry.correlation_id ? String(entry.correlation_id).trim() || null : null,
  )
  push(
    'ip_address',
    'IP address',
    entry.ip_address ? String(entry.ip_address).trim() || null : null,
  )

  const beforeSummary = formatSummaryMap(summarizeSafeObject(entry.before))
  push('before', 'Before', beforeSummary)
  const afterSummary = formatSummaryMap(summarizeSafeObject(entry.after))
  push('after', 'After', afterSummary)

  return fields
}

/** Allowlisted copy payload — never includes metadata/before/after/ip. */
export function buildAuditCopySummary(entry: AdminAuditEntry): AuditCopySummary {
  const summary: AuditCopySummary = {}
  if (entry.created_at) summary.timestamp = String(entry.created_at)
  if (entry.action) summary.action = String(entry.action)
  if (entry.outcome) summary.outcome = String(entry.outcome)
  const reason = controlledReasonCode(entry)
  if (reason) summary.reason = reason
  if (entry.actor_user_id != null) summary.actor_id = Number(entry.actor_user_id)
  if (entry.target_type) summary.target_type = String(entry.target_type)
  if (entry.target_id != null && entry.target_id !== '') {
    summary.target_id = String(entry.target_id)
  }
  if (entry.correlation_id) {
    const corr = String(entry.correlation_id).trim()
    if (corr) summary.correlation_id = corr
  }
  if (entry.capability) summary.capability = String(entry.capability)
  return summary
}

export function auditCopySummaryLine(entry: AdminAuditEntry): string {
  return JSON.stringify(buildAuditCopySummary(entry))
}
