/** Ordered unique correlation IDs from CRM events (newest-first list preserved). */
export function orderedUniqueCorrelationIds(
  events: Array<{ correlation_id?: string | null }>
): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const e of events) {
    const c = (e.correlation_id ?? '').trim()
    if (c && !seen.has(c)) {
      seen.add(c)
      out.push(c)
    }
  }
  return out
}

const SECTION_LABEL: Record<string, string> = {
  crm_events: 'CRM',
  automation_run_events: 'Automation',
  email_events: 'Email',
  ai_events: 'AI',
  automation_jobs: 'Job',
  chatbot_content_events: 'Chatbot'
}

export type TraceTimelineRow = {
  domain: string
  at: string
  title: string
  subtitle: string
  /** Original row for optional CRM / job shortcuts on the debug page. */
  raw?: Record<string, unknown>
}

/** In-app shortcut when a trace row clearly references a lead or automation job. */
export function getTraceRowQuickLink(
  row: Record<string, unknown> | undefined
): { to: string; label: string } | null {
  if (!row) return null
  const leadId = row.lead_id
  if (leadId != null && String(leadId).trim()) {
    return { to: '/crm', label: `CRM · lead ${leadId}` }
  }
  const runId = row.run_id
  if (runId != null && String(runId).trim()) {
    return { to: '/automations', label: `Automations · run ${runId}` }
  }
  const jobId = row.job_id
  if (jobId != null && String(jobId).trim()) {
    return { to: '/automations', label: `Automations · job ${jobId}` }
  }
  const et = String(row.entity_type ?? '').toLowerCase()
  const eid = row.entity_id
  if (eid != null && String(eid).trim() && (et === 'contact' || et === 'lead')) {
    return { to: '/crm', label: `CRM · ${et} ${eid}` }
  }
  return null
}

/** Flatten stitched trace sections into a readable timeline (newest first by timestamp string). */
export function flattenCorrelationTraceForTimeline(trace: {
  sections?: Record<string, unknown[]>
} | null): TraceTimelineRow[] {
  if (!trace?.sections) return []
  const rows: TraceTimelineRow[] = []
  for (const [sectionKey, items] of Object.entries(trace.sections)) {
    if (!Array.isArray(items)) continue
    const domain = SECTION_LABEL[sectionKey] ?? sectionKey
    for (const raw of items) {
      const r = raw as Record<string, unknown>
      const at = String(
        r.created_at ?? r.completed_at ?? r.started_at ?? ''
      )
      const title = String(
        r.event_type ?? r.status ?? r.payload_type ?? '(event)'
      )
      const subtitle = String(
        r.source ?? r.entity_type ?? r.provider ?? r.job_id ?? ''
      )
      rows.push({ domain, at, title, subtitle, raw: r })
    }
  }
  rows.sort((a, b) => b.at.localeCompare(a.at))
  return rows
}
