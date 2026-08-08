import { describe, expect, it } from 'vitest'
import { analyzeSectorInput } from '../lib/aboutSectorMatch'
import {
  SECTOR_FIT_GOLDEN_CORPUS,
  type SectorEvalCase,
} from './fixtures/sectorFitGoldenCorpus'

function runCase(testCase: SectorEvalCase) {
  const result = analyzeSectorInput(testCase.input)
  const presentation = result.presentation

  expect(presentation.status, testCase.notes ?? testCase.input).toBe(testCase.expectedStatus)

  if (testCase.expectedSectorId) {
    expect(presentation.sectorId, testCase.input).toBe(testCase.expectedSectorId)
  }

  if (testCase.forbiddenSectorIds?.length) {
    expect(testCase.forbiddenSectorIds).not.toContain(presentation.sectorId)
  }

  if (testCase.expectedStatus === 'invalid' || testCase.expectedStatus === 'needs_detail') {
    expect(presentation.sectorId).toBeNull()
  }

  if (testCase.expectedStatus === 'matched') {
    expect(presentation.matchStrength === 'high' || presentation.matchStrength === 'medium').toBe(
      true
    )
  }

  if (testCase.expectedStatus === 'ambiguous') {
    expect((presentation.ambiguousAlternates?.length ?? 0) >= 2).toBe(true)
  }
}

describe('sectorFit golden corpus', () => {
  it('covers the curated evaluation cases', () => {
    expect(SECTOR_FIT_GOLDEN_CORPUS.length).toBeGreaterThanOrEqual(80)
  })

  it.each(SECTOR_FIT_GOLDEN_CORPUS.map((c) => [c.input.slice(0, 48), c] as const))(
    'case: %s',
    (_label, testCase) => {
      runCase(testCase)
    }
  )
})
