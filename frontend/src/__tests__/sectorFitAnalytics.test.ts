import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildSectorExplorerResultPayload,
  getInputLengthBucket,
  trackSectorExplorerCta,
  trackSectorExplorerResult,
  trackSectorExplorerStarted,
  _resetSectorFitAnalyticsForTests,
  _setSectorFitAnalyticsTrackForTests,
} from '../lib/sectorFitAnalytics'
import { analyzeSectorInput } from '../lib/aboutSectorMatch'

describe('sectorFitAnalytics', () => {
  const track = vi.fn()

  beforeEach(() => {
    _resetSectorFitAnalyticsForTests()
    _setSectorFitAnalyticsTrackForTests(track)
    track.mockClear()
  })

  it('buckets input lengths without exposing raw text', () => {
    expect(getInputLengthBucket(0)).toBe('0')
    expect(getInputLengthBucket(1)).toBe('1-10')
    expect(getInputLengthBucket(10)).toBe('1-10')
    expect(getInputLengthBucket(11)).toBe('11-40')
    expect(getInputLengthBucket(41)).toBe('41-100')
    expect(getInputLengthBucket(101)).toBe('101+')
  })

  it('builds payloads without raw query fields', () => {
    const analysis = analyzeSectorInput('HVAC')
    const payload = buildSectorExplorerResultPayload({
      status: analysis.presentation.status,
      reasonCode: analysis.reasonCode,
      sectorId: analysis.presentation.sectorId,
      matchStrength: analysis.presentation.matchStrength,
      inputLength: 'HVAC'.length,
      usedFollowUp: false,
    })
    const serialized = JSON.stringify(payload)
    expect(serialized).not.toMatch(/HVAC/i)
    expect(payload).not.toHaveProperty('query')
    expect(payload).not.toHaveProperty('raw')
    expect(payload).not.toHaveProperty('normalizedInput')
    expect(payload.input_status).toBe('matched')
    expect(payload.sector_id).toBe('trades-home')
  })

  it('emits started only once until reset', async () => {
    trackSectorExplorerStarted()
    trackSectorExplorerStarted()
    await vi.waitFor(() => expect(track).toHaveBeenCalledTimes(1))
    expect(track).toHaveBeenCalledWith('sector_explorer_started', { surface: 'home' })
  })

  it('dedupes identical result fingerprints across rerenders', async () => {
    const payload = buildSectorExplorerResultPayload({
      status: 'matched',
      reasonCode: 'VALID_MATCH',
      sectorId: 'trades-home',
      matchStrength: 'high',
      inputLength: 4,
      usedFollowUp: false,
    })
    trackSectorExplorerResult(payload)
    trackSectorExplorerResult(payload)
    trackSectorExplorerResult({ ...payload })
    await vi.waitFor(() => expect(track).toHaveBeenCalledTimes(1))
    expect(track.mock.calls[0][0]).toBe('sector_explorer_result')
  })

  it('emits again when the meaningful result changes', async () => {
    trackSectorExplorerResult(
      buildSectorExplorerResultPayload({
        status: 'invalid',
        reasonCode: 'KEYBOARD_MASH',
        sectorId: null,
        matchStrength: null,
        inputLength: 9,
        usedFollowUp: false,
      })
    )
    trackSectorExplorerResult(
      buildSectorExplorerResultPayload({
        status: 'matched',
        reasonCode: 'VALID_MATCH',
        sectorId: 'trades-home',
        matchStrength: 'high',
        inputLength: 4,
        usedFollowUp: false,
      })
    )
    await vi.waitFor(() => expect(track).toHaveBeenCalledTimes(2))
  })

  it('does not emit idle results', async () => {
    trackSectorExplorerResult(
      buildSectorExplorerResultPayload({
        status: 'idle',
        reasonCode: 'EMPTY',
        sectorId: null,
        matchStrength: null,
        inputLength: 0,
        usedFollowUp: false,
      })
    )
    await new Promise((r) => setTimeout(r, 20))
    expect(track).not.toHaveBeenCalled()
  })

  it('never throws when the track sink throws', () => {
    _setSectorFitAnalyticsTrackForTests(() => {
      throw new Error('analytics down')
    })
    expect(() => trackSectorExplorerStarted()).not.toThrow()
    expect(() =>
      trackSectorExplorerResult(
        buildSectorExplorerResultPayload({
          status: 'unsupported',
          reasonCode: 'NO_SUPPORTED_SECTOR',
          sectorId: null,
          matchStrength: null,
          inputLength: 20,
          usedFollowUp: false,
        })
      )
    ).not.toThrow()
    expect(() => trackSectorExplorerCta('signup')).not.toThrow()
  })

  it('tracks CTAs with last status only (no raw input)', async () => {
    trackSectorExplorerResult(
      buildSectorExplorerResultPayload({
        status: 'matched',
        reasonCode: 'VALID_MATCH',
        sectorId: 'restaurant-hospitality',
        matchStrength: 'high',
        inputLength: 12,
        usedFollowUp: true,
      })
    )
    await vi.waitFor(() => expect(track).toHaveBeenCalled())
    track.mockClear()
    trackSectorExplorerCta('contact')
    await vi.waitFor(() => expect(track).toHaveBeenCalledTimes(1))
    const [, data] = track.mock.calls[0]
    expect(data).toMatchObject({
      cta: 'contact',
      used_follow_up: true,
      last_status: 'matched',
    })
    expect(JSON.stringify(data)).not.toMatch(/café|bakery|query/i)
  })

  it('does not alter analyzeSectorInput outcomes', () => {
    const before = analyzeSectorInput('MSP')
    trackSectorExplorerResult(
      buildSectorExplorerResultPayload({
        status: before.presentation.status,
        reasonCode: before.reasonCode,
        sectorId: before.presentation.sectorId,
        matchStrength: before.presentation.matchStrength,
        inputLength: 3,
        usedFollowUp: false,
      })
    )
    const after = analyzeSectorInput('MSP')
    expect(after).toEqual(before)
  })
})
