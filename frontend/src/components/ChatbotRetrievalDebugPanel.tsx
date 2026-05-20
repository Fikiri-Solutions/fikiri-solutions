import React from 'react'
import type { ChatbotRetrievalDebug } from '../services/apiClient'

const DEBUG_FIELDS: Array<{ key: keyof ChatbotRetrievalDebug; label: string }> = [
  { key: 'final_source_count', label: 'Final sources' },
  { key: 'raw_faq_count', label: 'Raw FAQ hits' },
  { key: 'raw_kb_count', label: 'Raw KB hits' },
  { key: 'raw_vector_count', label: 'Raw vector hits' },
  { key: 'post_vector_diversity_count', label: 'After vector diversity' },
  { key: 'post_cross_source_dedup_count', label: 'After cross-source dedup' },
  { key: 'collapsed_duplicate_count', label: 'Collapsed duplicates' },
  { key: 'retrieval_confidence', label: 'Retrieval confidence' },
  { key: 'context_char_count', label: 'Context chars' },
  { key: 'latency_ms', label: 'Latency (ms)' },
]

function formatDebugValue(key: keyof ChatbotRetrievalDebug, value: unknown): string {
  if (value === undefined || value === null) return '—'
  if (key === 'retrieval_confidence' && typeof value === 'number') {
    return `${Math.round(value * 1000) / 10}%`
  }
  return String(value)
}

type ChatbotRetrievalDebugPanelProps = {
  debug?: ChatbotRetrievalDebug | null
}

export const ChatbotRetrievalDebugPanel: React.FC<ChatbotRetrievalDebugPanelProps> = ({ debug }) => {
  if (!debug) {
    return (
      <div className="rounded-lg border border-dashed border-brand-text/20 dark:border-gray-600 p-3 text-xs text-brand-text/60 dark:text-gray-400">
        No retrieval debug data returned. Enable debug and run preview again.
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-brand-text/10 dark:border-gray-700 bg-brand-text/[0.02] dark:bg-gray-900/40 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-brand-text/60 dark:text-gray-400 mb-2">
        Retrieval debug
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {DEBUG_FIELDS.map(({ key, label }) => (
          <div key={key} className="contents">
            <dt className="text-brand-text/60 dark:text-gray-400">{label}</dt>
            <dd className="font-mono text-brand-text dark:text-gray-200 text-right">
              {formatDebugValue(key, debug[key])}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
