import { describe, expect, it } from 'vitest'
import {
  analyzeSectorInput,
  FEATURE_FIT_IDS,
  listSectorCatalog,
  MAX_MATCHING_INPUT_CHARS,
  MAX_RAW_INPUT_CHARS,
  normalizeForMatching,
  type SectorFitPresentation,
} from '../lib/aboutSectorMatch'
import { SECTOR_FIT_GOLDEN_CORPUS } from './fixtures/sectorFitGoldenCorpus'
import {
  SECTOR_EXPLORER_RELEASE_GATE,
  type SectorReleaseGateCase,
} from './fixtures/sectorFitReleaseGate'

function runReleaseGateCase(testCase: SectorReleaseGateCase) {
  const result = analyzeSectorInput(testCase.input)
  const presentation = result.presentation

  if (testCase.status) {
    expect(presentation.status, testCase.notes ?? testCase.input).toBe(testCase.status)
  }

  if (testCase.sectorId) {
    expect(presentation.sectorId, testCase.input).toBe(testCase.sectorId)
  }

  if (testCase.forbiddenSectorIds?.length) {
    expect(testCase.forbiddenSectorIds, testCase.notes ?? testCase.input).not.toContain(
      presentation.sectorId
    )
  }

  if (
    testCase.status === 'invalid' ||
    testCase.status === 'needs_detail' ||
    testCase.status === 'idle' ||
    testCase.status === 'unsupported' ||
    testCase.status === 'ambiguous'
  ) {
    // Non-matched statuses must not claim a confident authored sector fit list as personalized
    expect(presentation.sectorId).toBeNull()
  }
}

function expectNotMatched(input: string, forbiddenSectorId?: string) {
  const presentation = analyzeSectorInput(input).presentation
  expect(presentation.status, input).not.toBe('matched')
  if (forbiddenSectorId) {
    expect(presentation.sectorId).not.toBe(forbiddenSectorId)
  }
}

function expectMatchStrength(
  input: string,
  strength: SectorFitPresentation['matchStrength']
) {
  expect(analyzeSectorInput(input).presentation.matchStrength, input).toBe(strength)
}

function authoredSectorFits(presentation: SectorFitPresentation): boolean {
  // Matched results use sector-authored copy; fallback fits are shared across non-match states.
  return presentation.status === 'matched' && Boolean(presentation.sectorId)
}

describe('Sector Fit Explorer — release gate corpus', () => {
  it('stays intentionally small (25–40 cases)', () => {
    expect(SECTOR_EXPLORER_RELEASE_GATE.length).toBeGreaterThanOrEqual(25)
    expect(SECTOR_EXPLORER_RELEASE_GATE.length).toBeLessThanOrEqual(40)
  })

  it.each(SECTOR_EXPLORER_RELEASE_GATE.map((c) => [c.input.slice(0, 48) || '(empty)', c] as const))(
    'gate: %s',
    (_label, testCase) => {
      runReleaseGateCase(testCase)
    }
  )
})

describe('Sector Fit Explorer — invariants', () => {
  const pathological = [
    'こんにちは世界',
    'مرحبا بالعالم',
    'Здравствуй мир',
    'a'.repeat(10_000),
    '🔥'.repeat(200),
    '\uD800',
    'Hello\u0000World\u0001\u0002',
    '\u200B\u200C\u200D\uFEFF',
    '!!!@@@###$$$%%%^^^&&&***',
    'café café café — déjà vu',
    'HVAC'.repeat(300),
  ]

  it('never throws for arbitrary / pathological strings', () => {
    for (const input of pathological) {
      expect(() => analyzeSectorInput(input)).not.toThrow()
    }
  })

  it('is deterministic for the same input', () => {
    for (const input of [
      'HVAC',
      'food and beverage',
      'my company',
      'We’re a café / bakery!!!',
      'asdfghjkl',
    ]) {
      expect(analyzeSectorInput(input)).toEqual(analyzeSectorInput(input))
    }
  })

  it('does not change sector when only case changes', () => {
    for (const input of ['HVAC contractor', 'Family Dental Clinic', 'MSP managed IT']) {
      const lower = analyzeSectorInput(input.toLowerCase())
      const upper = analyzeSectorInput(input.toUpperCase())
      const mixed = analyzeSectorInput(input)
      expect(lower.presentation.sectorId).toBe(upper.presentation.sectorId)
      expect(lower.presentation.sectorId).toBe(mixed.presentation.sectorId)
      expect(lower.presentation.status).toBe(upper.presentation.status)
    }
  })

  it('does not change sector when only surrounding whitespace changes', () => {
    const base = analyzeSectorInput('gym')
    const padded = analyzeSectorInput('   gym   \n')
    expect(padded.presentation.sectorId).toBe(base.presentation.sectorId)
    expect(padded.presentation.status).toBe(base.presentation.status)
    expect(padded.presentation.matchStrength).toBe(base.presentation.matchStrength)
  })

  it('does not upgrade confidence when adding harmless punctuation', () => {
    const base = analyzeSectorInput('HVAC')
    const noisy = analyzeSectorInput('*** HVAC !!! ###')
    expect(noisy.presentation.status).toBe(base.presentation.status)
    expect(noisy.presentation.sectorId).toBe(base.presentation.sectorId)
    expect(noisy.presentation.matchStrength).toBe(base.presentation.matchStrength)
  })

  it('bounds raw and matching input lengths', () => {
    const huge = `HVAC ${'x'.repeat(5000)} contractor`
    const result = analyzeSectorInput(huge)
    expect(result.rawLength).toBeLessThanOrEqual(MAX_RAW_INPUT_CHARS)
    expect(result.matchingInput.length).toBeLessThanOrEqual(MAX_MATCHING_INPUT_CHARS)
  })

  it('only matched returns authored sector-specific fits', () => {
    const samples: Array<{ input: string; expectAuthored: boolean }> = [
      { input: '', expectAuthored: false },
      { input: 'asdfghjkl', expectAuthored: false },
      { input: 'my company', expectAuthored: false },
      { input: 'I sell rare antique maps', expectAuthored: false },
      { input: 'food and beverage', expectAuthored: false },
      { input: 'HVAC', expectAuthored: true },
    ]

    for (const sample of samples) {
      const presentation = analyzeSectorInput(sample.input).presentation
      expect(authoredSectorFits(presentation)).toBe(sample.expectAuthored)
      if (presentation.status === 'invalid' || presentation.status === 'unsupported') {
        expect(presentation.sectorId).toBeNull()
      }
      if (presentation.status === 'matched') {
        expect(presentation.sectorId).toBeTruthy()
        expect(presentation.featuresOrdered).toHaveLength(3)
        expect(presentation.featuresOrdered.every((f) => f.fit.trim().length > 0)).toBe(true)
      }
    }
  })
})

describe('Sector Fit Explorer — catalog integrity', () => {
  const catalog = listSectorCatalog()

  it('keeps the sector catalog structurally valid', () => {
    const ids = new Set<string>()

    expect(catalog.length).toBeGreaterThanOrEqual(20)

    for (const sector of catalog) {
      expect(ids.has(sector.id), `duplicate id ${sector.id}`).toBe(false)
      ids.add(sector.id)

      expect(sector.displayName.trim()).not.toBe('')
      expect(sector.category.trim()).not.toBe('')
      expect(sector.summary.trim()).not.toBe('')

      for (const featureId of FEATURE_FIT_IDS) {
        expect(sector.fits[featureId]?.trim().length, `${sector.id}.${featureId}`).toBeGreaterThan(0)
      }

      const seenConceptPairs = new Set<string>()
      expect(sector.keywords.length).toBeGreaterThan(0)

      for (const keyword of sector.keywords) {
        expect(['exact', 'token', 'phrase', 'prefix']).toContain(keyword.type)
        expect(keyword.value.trim()).not.toBe('')
        expect(normalizeForMatching(keyword.value)).not.toBe('')
        expect(keyword.conceptId.trim()).not.toBe('')
        expect(keyword.weight).toBeGreaterThan(0)

        if (keyword.type === 'prefix') {
          expect(normalizeForMatching(keyword.value).length).toBeGreaterThanOrEqual(4)
        }

        const pairKey = `${keyword.type}:${keyword.value}:${keyword.conceptId}`
        expect(seenConceptPairs.has(pairKey), `${sector.id} duplicate ${pairKey}`).toBe(false)
        seenConceptPairs.add(pairKey)
      }
    }
  })

  it('has a positive golden-corpus case for every sector id', () => {
    const covered = new Set(
      SECTOR_FIT_GOLDEN_CORPUS.filter((c) => c.expectedStatus === 'matched' && c.expectedSectorId).map(
        (c) => c.expectedSectorId as string
      )
    )
    for (const sector of catalog) {
      expect(covered.has(sector.id), `missing positive corpus case for ${sector.id}`).toBe(true)
    }
  })

  it('does not introduce unsupported feature ids', () => {
    for (const sector of catalog) {
      expect(Object.keys(sector.fits).sort()).toEqual([...FEATURE_FIT_IDS].sort())
    }
  })
})

describe('Sector Fit Explorer — false-confidence regressions', () => {
  it('does not match stacked generic business words', () => {
    expectMatchStrength('services business customer team', null)
    expectNotMatched('services business customer team')
  })

  it('does not match automation intent without a sector', () => {
    expectNotMatched('I need CRM and automation')
    expectNotMatched('want automation for my company')
  })

  it('does not match a company-name-only style phrase', () => {
    expectNotMatched('Acme Holdings LLC')
    expectNotMatched('MikeLarry Inc')
  })

  it('does not force hospitality from pub/inn collisions', () => {
    expectNotMatched('Public speaking coach', 'restaurant-hospitality')
    expectNotMatched('public relations consultancy', 'restaurant-hospitality')
  })

  it('does not force landscaping from yard embedded in unrelated words', () => {
    expectNotMatched('yardstick analytics', 'landscaping-field')
  })

  it('does not match when a short keyword is only embedded inside mash', () => {
    expectNotMatched('asdfghjklgymasdfghjkl', 'fitness-wellness')
    expectNotMatched('xxpubxx', 'restaurant-hospitality')
  })

  it('does not manufacture high confidence from duplicated concept forms alone beyond a real token', () => {
    // Concept dedupe: morphological repeats must not create an outsized fake-high path from weak stems only.
    const weakStemOnly = analyzeSectorInput('landscap')
    // Bare intentional stem without morphological extension stays non-high (needs detail or medium at most)
    expect(weakStemOnly.presentation.matchStrength).not.toBe('high')
  })

  it('never returns high confidence for insufficient or invalid inputs', () => {
    for (const input of [
      'my company',
      'we help people',
      'asdfghjkl',
      '123456789',
      'services business customer team',
    ]) {
      const presentation = analyzeSectorInput(input).presentation
      expect(presentation.matchStrength).not.toBe('high')
      expect(presentation.status).not.toBe('matched')
    }
  })
})
