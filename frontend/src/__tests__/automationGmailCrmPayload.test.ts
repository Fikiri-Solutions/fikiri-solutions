import { describe, it, expect } from 'vitest'
import {
  buildGmailCrmActionParameters,
  buildGmailCrmTriggerConditions,
  GMAIL_CRM_PRESET_ID,
} from '../lib/automationGmailCrmPayload'

describe('automationGmailCrmPayload', () => {
  it('builds slug-only trigger conditions when no filter', () => {
    const tc = buildGmailCrmTriggerConditions({ targetStage: 'new' })
    expect(tc).toEqual({ slug: GMAIL_CRM_PRESET_ID })
  })

  it('adds IF group for sender ends_with', () => {
    const tc = buildGmailCrmTriggerConditions({
      targetStage: 'new',
      senderEmailEndsWith: '@corp.com',
    })
    expect(tc.if).toEqual({
      match: 'all',
      conditions: [{ field: 'sender_email', op: 'ends_with', value: '@corp.com' }],
    })
  })

  it('builds action parameters with stage and slug', () => {
    const ap = buildGmailCrmActionParameters({ targetStage: 'qualified' })
    expect(ap).toMatchObject({
      target_stage: 'qualified',
      slug: GMAIL_CRM_PRESET_ID,
      tags: ['inbox'],
    })
  })
})
