import { describe, it, expect } from 'vitest'
import {
  flattenCorrelationTraceForTimeline,
  getTraceRowQuickLink,
  orderedUniqueCorrelationIds
} from '../utils/correlationTrace'

describe('correlationTrace utils', () => {
  it('orderedUniqueCorrelationIds preserves newest-first order and dedupes', () => {
    const ids = orderedUniqueCorrelationIds([
      { correlation_id: 'b' },
      { correlation_id: 'a' },
      { correlation_id: 'b' },
      { correlation_id: null },
      { correlation_id: '  a  ' }
    ])
    expect(ids).toEqual(['b', 'a'])
  })

  it('flattenCorrelationTraceForTimeline merges sections and sorts by created_at', () => {
    const rows = flattenCorrelationTraceForTimeline({
      sections: {
        crm_events: [
          { created_at: '2025-01-01T10:00:00', event_type: 'lead_created', source: 'api' },
          { created_at: '2025-01-02T10:00:00', event_type: 'stage_changed', source: 'user' }
        ],
        email_events: [{ created_at: '2025-01-01T12:00:00', event_type: 'sent', provider: 'gmail' }]
      }
    })
    expect(rows[0].at).toBe('2025-01-02T10:00:00')
    expect(rows[0].domain).toBe('CRM')
    expect(rows.some((r) => r.domain === 'Email')).toBe(true)
    const crmRow = rows.find((r) => r.title === 'lead_created')
    expect(crmRow?.raw).toEqual({
      created_at: '2025-01-01T10:00:00',
      event_type: 'lead_created',
      source: 'api'
    })
  })

  it('getTraceRowQuickLink prefers lead, then run, then job', () => {
    expect(getTraceRowQuickLink({ lead_id: 9, job_id: 'j1' })?.label).toContain('lead 9')
    expect(getTraceRowQuickLink({ run_id: 'r1', job_id: 'j1' })?.label).toContain('run r1')
    expect(getTraceRowQuickLink({ job_id: 'j2' })?.label).toContain('job j2')
    expect(getTraceRowQuickLink({ entity_type: 'contact', entity_id: 3 })?.label).toContain('contact 3')
    expect(getTraceRowQuickLink({ event_type: 'x' })).toBeNull()
  })
})
