import { beforeEach, describe, expect, it } from 'vitest'
import {
  INTAKE_DRAFT_STORAGE_KEY,
  applyPrefillToForm,
  buildIntakeHandoffPath,
  buildIntakeReviewLines,
  buildShortIntakePayload,
  buildWorkflowFocus,
  clearIntakeDraft,
  deriveLeadPriorityBand,
  primaryServiceFollowUp,
  readIntakeDraft,
  readPrefillFromSearch,
  serviceDetailLabel,
  writeIntakeDraft,
} from '../lib/consultationIntake'

describe('consultationIntake helpers', () => {
  beforeEach(() => {
    clearIntakeDraft()
  })

  it('prioritizes website follow-up when both website and software are selected', () => {
    expect(
      primaryServiceFollowUp(['custom_software_systems', 'website_design_development'])
    ).toBe('website')
    expect(primaryServiceFollowUp(['ai_business_automation'])).toBeNull()
    expect(primaryServiceFollowUp(['custom_software_systems'])).toBe('software')
  })

  it('maps short form into legacy intake contract without inventing business name', () => {
    const payload = buildShortIntakePayload({
      service_interests: ['website_design_development', 'ai_business_automation'],
      service_details: ['redesign', 'ecommerce'],
      industry: 'Retail / ecommerce',
      main_pain: 'Site leads never reach follow-up',
      contact_name: 'Alex',
      email: 'alex@example.com',
      phone: '',
      business_name: '',
      project_clarity: 'know_exactly',
      timeline_readiness: 'ready_now',
      budget_readiness: 'budget_ready',
      preferred_next_step: 'book',
      leave_blank: '',
    })
    expect(payload.business_name).toBeUndefined()
    expect(payload.contact_name).toBe('Alex')
    expect(payload.service_interests).toEqual([
      'website_design_development',
      'ai_business_automation',
    ])
    expect(payload.service_detail).toBe('redesign,ecommerce')
    expect(payload.project_clarity).toBe('know_exactly')
    expect(payload.budget_readiness).toBe('budget_ready')
    expect(payload.lead_priority_band).toBe('priority')
    expect(payload.preferred_next_step).toBe('book')
    expect(payload.workflow_focus).toContain('Website Design')
    expect(payload.main_pain).toContain('follow-up')
  })

  it('derives priority / warm / nurture bands for queue vetting', () => {
    expect(deriveLeadPriorityBand('know_exactly', 'ready_now', 'budget_ready')).toBe('priority')
    expect(deriveLeadPriorityBand('strong_idea', 'within_1_3_months', 'budget_ready')).toBe(
      'warm'
    )
    expect(deriveLeadPriorityBand('exploring', 'researching', 'not_sure')).toBe('nurture')
  })

  it('builds workflow focus labels from service ids', () => {
    expect(buildWorkflowFocus(['leads_customer_management'])).toBe(
      'Leads & Customer Management'
    )
  })

  it('reads chatbot-style query prefill', () => {
    const prefill = readPrefillFromSearch(
      '?industry=dental&pain=missed%20leads&email=a@b.co&name=Pat&source=site_chatbot'
    )
    expect(prefill.industry).toBe('dental')
    expect(prefill.main_pain).toBe('missed leads')
    expect(prefill.email).toBe('a@b.co')
    expect(prefill.contact_name).toBe('Pat')
    expect(prefill.source).toBe('site_chatbot')
  })

  it('appends intake handoff query params from chat slots', () => {
    const path = buildIntakeHandoffPath('/intake', {
      industry: 'HVAC',
      main_pain: 'quotes stall',
      contact_email: 'owner@shop.test',
      name: 'Jordan',
      business_name: 'Cool Air',
    })
    expect(path.startsWith('/intake?')).toBe(true)
    expect(path).toContain('industry=HVAC')
    expect(path).toContain('email=owner%40shop.test')
    expect(path).toContain('source=site_chatbot')
  })

  it('parses multi-service query prefill without inventing fields', () => {
    const prefill = readPrefillFromSearch(
      '?services=website_design_development,custom_software_systems&pain=need%20both'
    )
    expect(prefill.service_interests).toEqual([
      'website_design_development',
      'custom_software_systems',
    ])
    expect(prefill.main_pain).toBe('need both')
    expect(prefill.email).toBeUndefined()
    expect(prefill.business_name).toBeUndefined()
  })

  it('builds human review lines and detail labels', () => {
    expect(serviceDetailLabel('redesign')).toBe('Redesign')
    const lines = buildIntakeReviewLines({
      service_interests: ['website_design_development'],
      service_details: ['redesign'],
      industry: 'Retail / ecommerce',
      main_pain: 'Leads stall',
      contact_name: 'Alex',
      email: 'alex@example.com',
      phone: '',
      business_name: '',
      project_clarity: 'strong_idea',
      timeline_readiness: 'ready_now',
      budget_readiness: 'researching',
      preferred_next_step: '',
      leave_blank: '',
    })
    expect(lines.some((l) => l.includes('Website Design'))).toBe(true)
    expect(lines.some((l) => l.includes('Redesign'))).toBe(true)
    expect(lines.some((l) => l.includes('alex@example.com'))).toBe(true)
    expect(lines.some((l) => l.includes('Budget'))).toBe(true)
  })

  it('persists and restores draft without inventing business name', () => {
    clearIntakeDraft()
    writeIntakeDraft({
      step: 'contact',
      source: 'consultation_intake_short',
      form: {
        service_interests: ['ai_business_automation'],
        service_details: [],
        industry: '',
        main_pain: 'Too much manual work',
        contact_name: 'Sam',
        email: 'sam@example.com',
        phone: '',
        business_name: '',
        project_clarity: '',
        timeline_readiness: '',
        budget_readiness: '',
        preferred_next_step: '',
        leave_blank: 'should-not-persist',
      },
    })
    const draft = readIntakeDraft()
    expect(draft?.step).toBe('contact')
    expect(draft?.form.contact_name).toBe('Sam')
    expect(draft?.form.business_name).toBe('')
    expect(draft?.form.leave_blank).toBe('')
    expect(sessionStorage.getItem(INTAKE_DRAFT_STORAGE_KEY)).toBeTruthy()
    clearIntakeDraft()
    expect(readIntakeDraft()).toBeNull()
  })

  it('applies prefill over a base form without wiping unrelated fields', () => {
    const merged = applyPrefillToForm(
      {
        service_interests: ['scheduling_operations'],
        service_details: [],
        industry: 'Hospitality',
        main_pain: 'Keep me',
        contact_name: '',
        email: '',
        phone: '',
        business_name: '',
        project_clarity: '',
        timeline_readiness: '',
        budget_readiness: '',
        preferred_next_step: '',
        leave_blank: '',
      },
      { email: 'new@example.com', contact_name: 'New Name' }
    )
    expect(merged.email).toBe('new@example.com')
    expect(merged.contact_name).toBe('New Name')
    expect(merged.main_pain).toBe('Keep me')
    expect(merged.service_interests).toEqual(['scheduling_operations'])
  })
})
