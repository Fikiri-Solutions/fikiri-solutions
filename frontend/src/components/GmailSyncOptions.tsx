import React from 'react'
import type { GmailLookbackPreset, GmailSyncCursor } from '../services/apiClient'

export const DEFAULT_GMAIL_LOOKBACK_PRESETS: GmailLookbackPreset[] = [
  { id: '60d', label: 'Last 60 days', days: 60 },
  { id: '90d', label: 'Last 90 days', days: 90 },
  { id: '1y', label: 'Last year', days: 365 },
  { id: '2y', label: 'Last 2 years', days: 730 },
  { id: '5y', label: 'Last 5 years', days: 1825 },
]

type Props = {
  presets?: GmailLookbackPreset[]
  lookbackId: string
  onLookbackChange: (id: string) => void
  syncCursor?: GmailSyncCursor
  /** Last completed sync window (from API), if different from the selected dropdown. */
  activeLookbackLabel?: string | null
  disabled?: boolean
  pending?: boolean
  compact?: boolean
  onContinue?: () => void
}

export const GmailSyncOptions: React.FC<Props> = ({
  presets = DEFAULT_GMAIL_LOOKBACK_PRESETS,
  lookbackId,
  onLookbackChange,
  syncCursor,
  activeLookbackLabel,
  disabled,
  pending,
  compact,
  onContinue,
}) => {
  const hasMore = syncCursor?.has_more === true
  const selectedLabel = presets.find((p) => p.id === lookbackId)?.label ?? lookbackId
  const showActiveMismatch =
    Boolean(activeLookbackLabel && activeLookbackLabel !== selectedLabel && !pending)

  return (
    <div
      className={
        compact
          ? 'flex flex-wrap items-center gap-2'
          : 'flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3'
      }
    >
      {!compact && (
        <span className="text-xs font-medium text-brand-text/70 dark:text-gray-400">
          Import from
        </span>
      )}
      <select
        id="gmail-sync-lookback"
        name="gmail_sync_lookback"
        value={lookbackId}
        onChange={(e) => onLookbackChange(e.target.value)}
        disabled={disabled || pending}
        className="min-h-[40px] rounded-lg border border-brand-text/15 bg-white px-2 py-1.5 text-xs text-brand-text dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        aria-label="Email history range"
      >
        {presets.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </select>
      {hasMore && onContinue && (
        <button
          type="button"
          disabled={disabled || pending}
          onClick={onContinue}
          className="min-h-[40px] rounded-lg border border-brand-primary/40 px-2.5 py-1.5 text-xs font-medium text-brand-primary hover:bg-brand-primary/5 disabled:opacity-50 dark:text-orange-300"
        >
          Sync next batch
        </button>
      )}
      {showActiveMismatch && (
        <span className="w-full text-[11px] text-amber-700 dark:text-amber-300 sm:w-auto">
          Last sync used {activeLookbackLabel}. Use Update & sort in Organize to import {selectedLabel}.
        </span>
      )}
      {!compact && !showActiveMismatch && !pending && (
        <span className="text-[11px] text-brand-text/50 dark:text-gray-500">
          Changing the range applies on the next Update & sort in Organize.
        </span>
      )}
    </div>
  )
}
