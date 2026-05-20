import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createPreviewConversationId,
  mapPreviewQueryResult,
  previewSourceLabel,
  runChatbotBuilderPreview,
  runLegacyLocalPreview,
} from '../pages/chatbotBuilderPreview'

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
    previewChatbotQuery: vi.fn(),
    searchChatbotFaqs: vi.fn(),
    searchKnowledge: vi.fn(),
  },
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

describe('chatbotBuilderPreview helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('createPreviewConversationId returns a non-empty id', () => {
    const id = createPreviewConversationId()
    expect(id.length).toBeGreaterThan(8)
  })

  it('mapPreviewQueryResult maps production preview fields', () => {
    const mapped = mapPreviewQueryResult({
      success: true,
      answer: 'We are open 9-5.',
      confidence: 0.88,
      fallback_used: false,
      sources: [{ type: 'faq', id: 'f1', question: 'Hours?' }],
      config_applied: true,
    })
    expect(mapped.source).toBe('production')
    expect(mapped.answer).toBe('We are open 9-5.')
    expect(mapped.confidence).toBe(0.88)
    expect(mapped.fallbackUsed).toBe(false)
    expect(mapped.sources).toHaveLength(1)
  })

  it('mapPreviewQueryResult maps retrieval_debug when present', () => {
    const mapped = mapPreviewQueryResult({
      success: true,
      answer: 'We are open 9-5.',
      confidence: 0.88,
      fallback_used: false,
      sources: [{ type: 'faq', id: 'f1', question: 'Hours?' }],
      config_applied: true,
      retrieval_debug: {
        final_source_count: 1,
        raw_faq_count: 1,
        latency_ms: 12,
      },
    })
    expect(mapped.retrievalDebug?.final_source_count).toBe(1)
    expect(mapped.retrievalDebug?.latency_ms).toBe(12)
  })

  it('runChatbotBuilderPreview sends debug=true when requested', async () => {
    apiClientMock.previewChatbotQuery.mockResolvedValue({
      success: true,
      answer: 'Debug answer',
      confidence: 0.9,
      fallback_used: false,
      sources: [],
      config_applied: true,
      retrieval_debug: { final_source_count: 0 },
    })

    await runChatbotBuilderPreview('debug me', 'conv-1', { debug: true })

    expect(apiClientMock.previewChatbotQuery).toHaveBeenCalledWith('debug me', 'conv-1', { debug: true })
  })

  it('runChatbotBuilderPreview does not send debug when disabled', async () => {
    apiClientMock.previewChatbotQuery.mockResolvedValue({
      success: true,
      answer: 'Normal answer',
      confidence: 0.9,
      fallback_used: false,
      sources: [],
      config_applied: true,
    })

    await runChatbotBuilderPreview('no debug', undefined, { debug: false })

    expect(apiClientMock.previewChatbotQuery).toHaveBeenCalledWith('no debug', undefined, { debug: false })
  })

  it('previewSourceLabel reflects fallback_used on production preview', () => {
    expect(previewSourceLabel('production', false)).toBe('Production preview')
    expect(previewSourceLabel('production', true)).toBe('Production preview · fallback')
  })

  it('runChatbotBuilderPreview calls preview-query with query', async () => {
    apiClientMock.previewChatbotQuery.mockResolvedValue({
      success: true,
      answer: 'Live brain answer',
      confidence: 0.9,
      fallback_used: false,
      sources: [],
      config_applied: true,
    })

    const result = await runChatbotBuilderPreview('What are your hours?')

    expect(apiClientMock.previewChatbotQuery).toHaveBeenCalledWith('What are your hours?', undefined, undefined)
    expect(result.botPreview.answer).toBe('Live brain answer')
    expect(result.botPreview.source).toBe('production')
  })

  it('runChatbotBuilderPreview forwards optional conversation_id', async () => {
    apiClientMock.previewChatbotQuery.mockResolvedValue({
      success: true,
      answer: 'Follow-up answer',
      confidence: 0.85,
      fallback_used: false,
      sources: [],
      config_applied: true,
    })

    await runChatbotBuilderPreview('follow up?', 'conv-abc')

    expect(apiClientMock.previewChatbotQuery).toHaveBeenCalledWith('follow up?', 'conv-abc', undefined)
  })

  it('runChatbotBuilderPreview handles fallback_used=true without throwing', async () => {
    apiClientMock.previewChatbotQuery.mockResolvedValue({
      success: true,
      answer: 'I may be missing context.',
      confidence: 0.2,
      fallback_used: true,
      sources: [],
      config_applied: true,
    })

    const result = await runChatbotBuilderPreview('unknown topic')

    expect(result.botPreview.fallbackUsed).toBe(true)
    expect(result.botPreview.answer).toContain('missing context')
  })

  it('runChatbotBuilderPreview falls back to legacy FAQ/KB when preview-query fails', async () => {
    apiClientMock.previewChatbotQuery.mockRejectedValue(new Error('network'))
    apiClientMock.searchChatbotFaqs.mockResolvedValue({
      best_match: { question: 'Q', answer: 'Legacy FAQ', confidence: 0.7 },
    })

    const result = await runChatbotBuilderPreview('hours?', 'conv-persist')

    expect(apiClientMock.previewChatbotQuery).toHaveBeenCalledWith('hours?', 'conv-persist', undefined)
    expect(apiClientMock.searchChatbotFaqs).toHaveBeenCalled()
    expect(result.botPreview.source).toBe('faq')
    expect(result.botPreview.answer).toBe('Legacy FAQ')
  })

  it('runLegacyLocalPreview uses knowledge when no FAQ match', async () => {
    apiClientMock.searchChatbotFaqs.mockResolvedValue({ best_match: null, fallback_response: 'none' })
    apiClientMock.searchKnowledge.mockResolvedValue([
      {
        document_id: 'd1',
        title: 'Pricing doc',
        summary: 'Starts at $49',
        content_preview: 'Our plans start at $49.',
        relevance_score: 0.8,
        category: 'general',
      },
    ])

    const result = await runLegacyLocalPreview('pricing')

    expect(result.botPreview.source).toBe('knowledge')
    expect(result.searchResults).toHaveLength(1)
  })
})
