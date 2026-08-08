import { describe, expect, it } from 'vitest'
import {
  analyzeSectorInput,
  combineSectorQueries,
  getSectorFitPresentation,
  MAX_RAW_INPUT_CHARS,
  normalizeForMatching,
  normalizeForValidation,
  scoreSectorMatchById,
} from '../lib/aboutSectorMatch'

describe('aboutSectorMatch', () => {
  it('returns idle empty-state when query is blank', () => {
    const fit = getSectorFitPresentation('')
    expect(fit.status).toBe('idle')
    expect(fit.headline).toBe('Tell us what your business does')
    expect(fit.matchStrength).toBeNull()
  })

  it('matches trades keywords for HVAC descriptions', () => {
    const fit = getSectorFitPresentation('we run a small HVAC company')
    expect(fit.status).toBe('matched')
    expect(fit.headline).toContain('Trades & home services')
    expect(fit.matchStrength).not.toBeNull()
    expect(fit.matchStrength).not.toBe('broad')
    expect(fit.sectorId).toBe('trades-home')
  })

  it('flags unsupported niche businesses without forcing a sector', () => {
    const fit = getSectorFitPresentation('custom underwater basket weaving cooperative')
    expect(fit.status).toBe('unsupported')
    expect(fit.needsMoreDetail).toBe(true)
    expect(fit.sectorId).toBeNull()
  })

  it('combines primary and follow-up text for scoring', () => {
    const vague = getSectorFitPresentation('we help local businesses grow')
    expect(vague.status).toBe('needs_detail')
    expect(vague.needsMoreDetail).toBe(true)

    const combined = getSectorFitPresentation(
      combineSectorQueries('we help local businesses grow', 'family dental clinic appointments by email')
    )
    expect(combined.status).toBe('matched')
    expect(combined.needsMoreDetail).toBe(false)
  })

  it('matches common single-word and creator phrases', () => {
    expect(getSectorFitPresentation('trainer').status).toBe('matched')
    expect(getSectorFitPresentation('content creator').headline).toContain('Creators')
    expect(getSectorFitPresentation('gym').status).toBe('matched')
  })

  it('maps automotive and service-industry language to the right buckets', () => {
    const auto = getSectorFitPresentation('car dealership service department')
    expect(auto.category).toBe('Automotive')
    expect(auto.status).toBe('matched')

    const field = getSectorFitPresentation('field service dispatch for commercial clients')
    expect(field.category).toBe('Service industry')
    expect(field.headline).toContain('Field crews')
  })

  it('does not match vague service-only wording to a vertical', () => {
    const fit = getSectorFitPresentation('we provide service')
    expect(fit.status).toBe('needs_detail')
    expect(fit.needsMoreDetail).toBe(true)
    expect(fit.sectorId).toBeNull()
  })

  it('asks for detail when two sectors score similarly instead of guessing', () => {
    const fit = getSectorFitPresentation('food and beverage')
    expect(fit.status).toBe('ambiguous')
    expect(fit.ambiguousAlternates?.length).toBeGreaterThanOrEqual(2)
  })

  it('scores landscaping examples as a high-confidence match', () => {
    const fit = getSectorFitPresentation('Landscaping and seasonal cleanup')
    expect(fit.status).toBe('matched')
    expect(fit.matchStrength).toBe('high')
    expect(fit.sectorId).toBe('landscaping-field')
    expect(scoreSectorMatchById('landscaping and seasonal cleanup', 'landscaping-field')).toBeGreaterThan(0)
  })
  it('does not block sector labels that also look like generic business words', () => {
    expect(getSectorFitPresentation('restaurant').status).toBe('matched')
    expect(getSectorFitPresentation('restaurant').sectorId).toBe('restaurant-hospitality')
    expect(getSectorFitPresentation('clinic').sectorId).toBe('medical-clinical')
    expect(getSectorFitPresentation('software company').sectorId).toBe('saas-tech-product')
  })
})

describe('analyzeSectorInput viability', () => {
  it('treats whitespace and invisible characters as empty', () => {
    for (const input of ['', '   ', '\t\n', '\u00A0\u00A0', '\u200B\u200B', '  \uFEFF  ']) {
      const result = analyzeSectorInput(input)
      expect(result.status).toBe('empty')
      expect(result.reasonCode).toBe('EMPTY')
      expect(result.presentation.sectorId).toBeNull()
    }
  })

  it('rejects symbols-only and emoji-only input', () => {
    for (const input of ['!!!', '---', '$$$', '🔥🔥🔥', '...///...']) {
      const result = analyzeSectorInput(input)
      expect(result.status).toBe('nonsensical')
      expect(result.presentation.status).toBe('invalid')
      expect(result.presentation.sectorId).toBeNull()
    }
  })

  it('rejects numbers-only but allows numbers mixed with text', () => {
    expect(analyzeSectorInput('123456789').reasonCode).toBe('ONLY_NUMBERS')
    expect(analyzeSectorInput('24 hour towing').status).toBe('matched')
    expect(analyzeSectorInput('3D printing company').status).not.toBe('nonsensical')
    expect(analyzeSectorInput('B2B software').status).toBe('matched')
  })

  it('rejects keyboard mash and repeated noise', () => {
    for (const input of ['asdfghjkl', 'qwertyuiop', 'zxcvbnm', 'aaaaaaaaaaaa', 'abababababababab']) {
      const result = analyzeSectorInput(input)
      expect(result.presentation.status).toBe('invalid')
      expect(result.presentation.sectorId).toBeNull()
    }
  })

  it('keeps approved short aliases matchable', () => {
    for (const input of ['gym', 'CPA', 'MSP', 'HVAC', 'SaaS']) {
      const result = analyzeSectorInput(input)
      expect(result.status).toBe('matched')
      expect(result.presentation.sectorId).toBeTruthy()
    }
  })

  it('does not call unusual brand-like names nonsense when paired with sector terms', () => {
    expect(analyzeSectorInput('Xtreme HVAC').status).toBe('matched')
    expect(analyzeSectorInput('K9 training').status).not.toBe('nonsensical')
  })

  it('caps raw input length without throwing', () => {
    const huge = `${'HVAC '.repeat(200)}contractor`
    const result = analyzeSectorInput(huge)
    expect(result.rawLength).toBeLessThanOrEqual(MAX_RAW_INPUT_CHARS)
    expect(result.matchingInput.length).toBeLessThanOrEqual(300)
    expect(() => analyzeSectorInput(huge)).not.toThrow()
  })

  it('normalizes accented English for matching', () => {
    expect(normalizeForMatching('Café & Bakery')).toBe('cafe and bakery')
    expect(normalizeForMatching('Déjà Vu Salon')).toContain('deja vu salon')
    expect(normalizeForMatching('HVAC—Plumbing')).toContain('hvac')
    expect(analyzeSectorInput('Café & Bakery').status).toBe('matched')
    expect(analyzeSectorInput('We’re a café / bakery!!!').status).toBe('matched')
  })

  it('preserves readable unicode in validation form and strips controls', () => {
    const cleaned = normalizeForValidation('Hello\u0000World')
    expect(cleaned).not.toContain('\u0000')
  })

  it('does not label non-English letters as keyboard mash', () => {
    const result = analyzeSectorInput('私たちは清掃会社です')
    expect(result.reasonCode).not.toBe('KEYBOARD_MASH')
    expect(result.presentation.status).toBe('needs_detail')
  })

  it('returns unsupported for viable but unmatched niches', () => {
    const result = analyzeSectorInput('I sell rare antique maps')
    expect(result.status).toBe('unsupported')
    expect(result.presentation.headline).toContain('do not have a specific sector match')
  })

  it('returns needs_detail for insufficient descriptions', () => {
    for (const input of ['my company', 'we help people', 'automation', 'small local business']) {
      const result = analyzeSectorInput(input)
      expect(result.presentation.status).toBe('needs_detail')
      expect(result.presentation.sectorId).toBeNull()
    }
  })

  it('avoids short-keyword substring collisions', () => {
    // "pub" must not match inside "public" / unrelated words as a sector force
    const publicWorks = analyzeSectorInput('public speaking coach for executives')
    expect(publicWorks.presentation.sectorId).not.toBe('restaurant-hospitality')

    // "inn" must not match inside "winning"
    const winning = analyzeSectorInput('winning sales strategies consulting')
    expect(winning.presentation.sectorId).not.toBe('restaurant-hospitality')
  })

  it('is deterministic and never throws on pathological strings', () => {
    const samples = [
      '\uD800', // lone surrogate
      'a'.repeat(10000),
      '🔥'.repeat(100),
      '*** &&& /// !!!',
      'restaurant and food distributor',
    ]
    for (const input of samples) {
      expect(() => analyzeSectorInput(input)).not.toThrow()
      const a = analyzeSectorInput(input)
      const b = analyzeSectorInput(input)
      expect(a).toEqual(b)
    }
  })

  it('does not upgrade confidence when appending random symbols', () => {
    const base = analyzeSectorInput('HVAC')
    const noisy = analyzeSectorInput('HVAC *** !!! ###')
    expect(base.status).toBe('matched')
    expect(noisy.status).toBe('matched')
    expect(noisy.presentation.sectorId).toBe(base.presentation.sectorId)
  })
})
