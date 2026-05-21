import { describe, it, expect } from 'vitest'
import {
  humanPriorityTag,
  organizeAttentionCount,
  queueCount,
  ORGANIZE_QUEUES,
} from '../constants/inboxSimpleFirst'

describe('inboxSimpleFirst', () => {
  it('sums queue counts from backend category_counts', () => {
    const counts = {
      business_lead: 3,
      action_needed: 2,
      existing_client: 1,
      newsletter_marketing: 10,
      personal_non_business: 4,
      spam_risk: 1,
      review_needed: 2,
    }
    expect(queueCount(counts, ORGANIZE_QUEUES[0])).toBe(3)
    expect(queueCount(counts, ORGANIZE_QUEUES[1])).toBe(3)
    expect(queueCount(counts, ORGANIZE_QUEUES[2])).toBe(15)
    expect(organizeAttentionCount(counts)).toBe(23)
  })

  it('maps scores to calm human tags', () => {
    expect(
      humanPriorityTag(
        { lead_score: 80, urgency_score: 10, confidence: 0.9, category: 'business_lead' },
        'opportunities'
      )
    ).toBe('Strong lead')
    expect(
      humanPriorityTag(
        { lead_score: 10, urgency_score: 70, confidence: 0.9, category: 'action_needed' },
        'needs_reply'
      )
    ).toBe('Reply today')
    expect(
      humanPriorityTag(
        { lead_score: 10, urgency_score: 10, confidence: 0.4, category: 'review_needed' },
        'not_sure'
      )
    ).toBe('Not sure')
  })
})
