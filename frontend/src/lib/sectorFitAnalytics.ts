/**
 * Privacy-safe Sector Fit Explorer analytics (Phase 4).
 *
 * Observational only — must never affect matching, delay UI, or include raw input.
 * Vercel Analytics is disabled (usage-billed on Pro). Tracking is a no-op unless a
 * test injects a sink via _setSectorFitAnalyticsTrackForTests.
 */

import type {
  SectorFitPresentationStatus,
  SectorInputReasonCode,
} from './aboutSectorMatch'

export type SectorExplorerInputLengthBucket = '0' | '1-10' | '11-40' | '41-100' | '101+'

export type SectorExplorerCta = 'contact' | 'signup' | 'pricing' | 'intake' | 'intake'

export type SectorExplorerResultPayload = {
  input_status: SectorFitPresentationStatus
  reason_code: string
  sector_id: string
  match_strength: string
  input_length_bucket: SectorExplorerInputLengthBucket
  used_follow_up: boolean
}

type TrackFn = (event: string, data?: Record<string, string | number | boolean | null>) => void

let lastResultFingerprint = ''
let lastUsedFollowUp = false
let startedEmitted = false
let trackImpl: TrackFn | null | undefined

/** Override sink for tests; pass null to clear. */
export function _setSectorFitAnalyticsTrackForTests(track: TrackFn | null): void {
  trackImpl = track
}

export function _resetSectorFitAnalyticsForTests(): void {
  lastResultFingerprint = ''
  lastUsedFollowUp = false
  startedEmitted = false
  trackImpl = null
}

export function getInputLengthBucket(length: number): SectorExplorerInputLengthBucket {
  const n = Math.max(0, Math.floor(length))
  if (n === 0) return '0'
  if (n <= 10) return '1-10'
  if (n <= 40) return '11-40'
  if (n <= 100) return '41-100'
  return '101+'
}

export function buildSectorExplorerResultPayload(args: {
  status: SectorFitPresentationStatus
  reasonCode: SectorInputReasonCode | null
  sectorId: string | null
  matchStrength: 'high' | 'medium' | 'broad' | null
  inputLength: number
  usedFollowUp: boolean
}): SectorExplorerResultPayload {
  return {
    input_status: args.status,
    reason_code: args.reasonCode ?? '',
    sector_id: args.sectorId ?? '',
    match_strength: args.matchStrength ?? '',
    input_length_bucket: getInputLengthBucket(args.inputLength),
    used_follow_up: args.usedFollowUp,
  }
}

function resultFingerprint(payload: SectorExplorerResultPayload): string {
  return [
    payload.input_status,
    payload.reason_code,
    payload.sector_id,
    payload.match_strength,
    payload.used_follow_up ? '1' : '0',
  ].join(':')
}

function emitSafe(eventName: string, data: Record<string, string | number | boolean | null>): void {
  try {
    const track = trackImpl
    if (!track) return
    track(eventName, data)
  } catch {
    // Analytics must never break the explorer
  }
}

/** Once per page mount / tab until reset — explorer became interactive surface. */
export function trackSectorExplorerStarted(): void {
  if (startedEmitted) return
  startedEmitted = true
  emitSafe('sector_explorer_started', { surface: 'home' })
}

/**
 * Emit after a meaningful presentation status change (not every keystroke).
 * Dedupes identical fingerprints across React rerenders.
 */
export function trackSectorExplorerResult(payload: SectorExplorerResultPayload): void {
  if (payload.input_status === 'idle') return
  const fingerprint = resultFingerprint(payload)
  if (fingerprint === lastResultFingerprint) return
  lastResultFingerprint = fingerprint
  lastUsedFollowUp = payload.used_follow_up
  emitSafe('sector_explorer_result', {
    input_status: payload.input_status,
    reason_code: payload.reason_code,
    sector_id: payload.sector_id,
    match_strength: payload.match_strength,
    input_length_bucket: payload.input_length_bucket,
    used_follow_up: payload.used_follow_up,
  })
}

export function trackSectorExplorerCta(cta: SectorExplorerCta): void {
  emitSafe('sector_explorer_cta', {
    cta,
    used_follow_up: lastUsedFollowUp,
    last_status: lastResultFingerprint ? lastResultFingerprint.split(':')[0] : '',
  })
}
