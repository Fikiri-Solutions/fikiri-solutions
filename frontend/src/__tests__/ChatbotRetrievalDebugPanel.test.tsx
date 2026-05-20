import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatbotRetrievalDebugPanel } from '../components/ChatbotRetrievalDebugPanel'

describe('ChatbotRetrievalDebugPanel', () => {
  it('renders returned debug fields', () => {
    render(
      <ChatbotRetrievalDebugPanel
        debug={{
          final_source_count: 2,
          raw_faq_count: 1,
          raw_kb_count: 1,
          raw_vector_count: 3,
          post_vector_diversity_count: 2,
          post_cross_source_dedup_count: 2,
          collapsed_duplicate_count: 1,
          retrieval_confidence: 0.8125,
          context_char_count: 420,
          latency_ms: 35,
        }}
      />
    )

    expect(screen.getByText('Retrieval debug')).toBeInTheDocument()
    expect(screen.getByText('Final sources')).toBeInTheDocument()
    expect(screen.getByText('81.3%')).toBeInTheDocument()
    expect(screen.getByText('Collapsed duplicates')).toBeInTheDocument()
    expect(screen.getByText('Latency (ms)')).toBeInTheDocument()
    expect(screen.getByText('420')).toBeInTheDocument()
    expect(screen.getByText('35')).toBeInTheDocument()
  })

  it('does not crash when retrieval_debug is missing', () => {
    render(<ChatbotRetrievalDebugPanel debug={undefined} />)
    expect(screen.getByText(/No retrieval debug data returned/)).toBeInTheDocument()
  })
})
