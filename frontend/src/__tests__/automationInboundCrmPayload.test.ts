import { describe, it, expect } from 'vitest'
import {
  buildInboundCrmSyncActionParameters,
  buildInboundCrmSyncTriggerConditions,
  INBOUND_CRM_SYNC_PRESET_ID,
} from '../lib/automationInboundCrmPayload'

describe('automationInboundCrmPayload', () => {
  it('builds slug-only trigger conditions when no filter', () => {
    const tc = buildInboundCrmSyncTriggerConditions({ targetStage: 'new' })
    expect(tc).toEqual({ slug: INBOUND_CRM_SYNC_PRESET_ID })
  })

  it('adds IF group for sender ends_with', () => {
    const tc = buildInboundCrmSyncTriggerConditions({
      targetStage: 'new',
      senderEmailEndsWith: '@corp.com',
    })
    expect(tc.if).toEqual({
      match: 'all',
      conditions: [{ field: 'sender_email', op: 'ends_with', value: '@corp.com' }],
    })
  })

  it('builds action parameters with stage and slug', () => {
    const ap = buildInboundCrmSyncActionParameters({ targetStage: 'qualified' })
    expect(ap).toMatchObject({
      target_stage: 'qualified',
      slug: INBOUND_CRM_SYNC_PRESET_ID,
      tags: ['inbox'],
    })
  })
})
