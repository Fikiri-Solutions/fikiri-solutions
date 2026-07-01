import { describe, expect, it } from 'vitest'
import { formatSiteChatTranscript } from '../utils/siteChatDevTools'

describe('siteChatDevTools', () => {
  it('formats transcript with session and roles', () => {
    const text = formatSiteChatTranscript(
      'site_abc',
      [
        { role: 'assistant', text: 'Welcome.' },
        { role: 'user', text: 'Pricing?' },
      ],
      {
        schema_version: 'v1',
        session_id: 'site_abc',
        mode: 'answer',
        response: 'x',
        handoff: { applicable: false },
        lead_intent: {},
        lead_assessment: {
          score: 1,
          tier: 'casual',
          signals: ['pricing_interest'],
          synopsis: 'Visitor asked about pricing; business context not yet captured.',
          recommended_handoff: null,
        },
        turn_count: 1,
        grounded: true,
        confidence: 0.8,
      }
    )
    expect(text).toContain('session_id: site_abc')
    expect(text).toContain('User: Pricing?')
    expect(text).toContain('Assistant: Welcome.')
    expect(text).toContain('last_mode: answer')
    expect(text).toContain('lead_assessment: score=1 tier=casual')
    expect(text).toContain('lead_synopsis:')
  })
})
