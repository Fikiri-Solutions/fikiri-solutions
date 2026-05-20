import type { GmailLookbackPreset } from '../services/apiClient'

export const GMAIL_LOOKBACK_STORAGE_KEY = 'fikiri-gmail-lookback-id'

const VALID_IDS = new Set(['60d', '90d', '1y', '2y', '5y'])

export function loadGmailLookbackId(fallback = '90d'): string {
  if (typeof window === 'undefined') return fallback
  try {
    const stored = localStorage.getItem(GMAIL_LOOKBACK_STORAGE_KEY)
    if (stored && VALID_IDS.has(stored)) return stored
  } catch {
    // ignore
  }
  return fallback
}

export function saveGmailLookbackId(id: string): void {
  if (typeof window === 'undefined' || !VALID_IDS.has(id)) return
  try {
    localStorage.setItem(GMAIL_LOOKBACK_STORAGE_KEY, id)
  } catch {
    // ignore
  }
}

/** Map API sync_cursor.lookback_days to preset id when possible. */
export function lookbackIdFromDays(
  days: number | undefined,
  presets: GmailLookbackPreset[]
): string | null {
  if (days == null || !Number.isFinite(days)) return null
  const match = presets.find((p) => p.days === days)
  return match?.id ?? null
}

export function labelForLookbackId(id: string, presets: GmailLookbackPreset[]): string {
  return presets.find((p) => p.id === id)?.label ?? id
}
