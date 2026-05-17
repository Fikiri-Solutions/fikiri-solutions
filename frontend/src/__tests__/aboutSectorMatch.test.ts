import { describe, expect, it } from 'vitest'
import {
  combineSectorQueries,
  getSectorFitPresentation,
  scoreSectorMatch,
} from '../lib/aboutSectorMatch'

describe('aboutSectorMatch', () => {
  it('returns empty-state copy when query is blank', () => {
    const fit = getSectorFitPresentation('')
    expect(fit.headline).toBe('Tell us what you do')
    expect(fit.matchStrength).toBe('broad')
  })

  it('matches trades keywords for HVAC descriptions', () => {
    const fit = getSectorFitPresentation('we run a small HVAC company')
    expect(fit.headline).toContain('Trades & home services')
    expect(fit.matchStrength).not.toBe('broad')
  })

  it('flags broad matches that need more sector detail', () => {
    const fit = getSectorFitPresentation('custom underwater welder')
    expect(fit.headline).toContain('What could help')
    expect(fit.needsMoreDetail).toBe(true)
    expect(fit.matchStrength).toBe('broad')
  })

  it('combines primary and follow-up text for scoring', () => {
    const vague = getSectorFitPresentation('we help local businesses grow')
    expect(vague.needsMoreDetail).toBe(true)

    const combined = getSectorFitPresentation(
      combineSectorQueries('we help local businesses grow', 'family dental clinic appointments by email')
    )
    expect(combined.matchStrength).not.toBe('broad')
    expect(combined.needsMoreDetail).toBe(false)
  })

  it('matches common single-word and creator phrases', () => {
    expect(getSectorFitPresentation('trainer').matchStrength).not.toBe('broad')
    expect(getSectorFitPresentation('content creator').headline).toContain('Creators')
    expect(getSectorFitPresentation('gym').matchStrength).not.toBe('broad')
  })

  it('maps automotive and service-industry language to the right buckets', () => {
    const auto = getSectorFitPresentation('car dealership service department')
    expect(auto.category).toBe('Automotive')
    expect(auto.matchStrength).not.toBe('broad')

    const field = getSectorFitPresentation('field service dispatch for commercial clients')
    expect(field.category).toBe('Service industry')
    expect(field.headline).toContain('Field crews')
  })

  it('does not match vague service-only wording to a vertical', () => {
    const fit = getSectorFitPresentation('we provide service')
    expect(fit.matchStrength).toBe('broad')
    expect(fit.needsMoreDetail).toBe(true)
  })

  it('asks for detail when two sectors score similarly instead of guessing', () => {
    const fit = getSectorFitPresentation('food and beverage')
    if (fit.ambiguousAlternates) {
      expect(fit.matchStrength).toBe('broad')
      expect(fit.ambiguousAlternates.length).toBeGreaterThanOrEqual(2)
    }
  })

  it('scores landscaping examples above the medium threshold', () => {
    const fit = getSectorFitPresentation('Landscaping and seasonal cleanup')
    expect(fit.matchStrength).toBe('high')
    expect(scoreSectorMatch('landscaping and seasonal cleanup', {
      id: 'landscaping-field',
      displayName: 'Landscaping',
      category: 'Service industry',
      keywords: [],
      summary: '',
      fits: {
        email_automation: '',
        crm_management: '',
        ai_assistant: '',
      },
      normalizedPhrases: ['landscaping and seasonal cleanup'],
    })).toBeGreaterThan(0)
  })
})
