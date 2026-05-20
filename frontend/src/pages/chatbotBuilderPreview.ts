import {
  apiClient,
  ChatbotPreviewQueryResult,
  ChatbotPreviewSource,
  KnowledgeSearchResult,
} from '../services/apiClient'

export type BotPreviewSourceKind = 'faq' | 'knowledge' | 'fallback' | 'production'

export type BotPreview = {
  answer: string
  confidence?: number
  source: BotPreviewSourceKind
  question?: string
  fallbackUsed?: boolean
  sources?: ChatbotPreviewSource[]
}

export function createPreviewConversationId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `preview-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
}

export function previewSourceLabel(source: BotPreviewSourceKind, fallbackUsed?: boolean): string {
  if (source === 'production') {
    return fallbackUsed ? 'Production preview · fallback' : 'Production preview'
  }
  if (source === 'faq') return 'FAQ match'
  if (source === 'knowledge') return 'Knowledge'
  return 'Fallback'
}

export function mapPreviewQueryResult(result: ChatbotPreviewQueryResult): BotPreview {
  return {
    answer: result.answer,
    confidence: result.confidence,
    source: 'production',
    fallbackUsed: result.fallback_used,
    sources: result.sources ?? [],
  }
}

/** Legacy FAQ → KB local preview when preview-query is unavailable. */
export async function runLegacyLocalPreview(query: string): Promise<{
  botPreview: BotPreview
  searchResults: KnowledgeSearchResult[]
}> {
  const faq = await apiClient.searchChatbotFaqs(query.trim(), 3)
  const best = faq.best_match
  if (best?.answer) {
    return {
      botPreview: {
        answer: best.answer,
        confidence: best.confidence,
        source: 'faq',
        question: best.question,
      },
      searchResults: [],
    }
  }

  const results = await apiClient.searchKnowledge(query.trim())
  if (results.length > 0) {
    const top = results[0]
    return {
      botPreview: {
        answer: top.content_preview || top.summary || 'No answer text in this document.',
        source: 'knowledge',
        question: top.title,
      },
      searchResults: results,
    }
  }

  return {
    botPreview: {
      answer:
        faq.fallback_response ||
        'No matching FAQ or knowledge document yet. Add content above and try again.',
      source: 'fallback',
    },
    searchResults: [],
  }
}

export async function runChatbotBuilderPreview(
  query: string,
  conversationId?: string
): Promise<{
  botPreview: BotPreview
  searchResults: KnowledgeSearchResult[]
}> {
  try {
    const result = await apiClient.previewChatbotQuery(query.trim(), conversationId)
    return {
      botPreview: mapPreviewQueryResult(result),
      searchResults: [],
    }
  } catch {
    return runLegacyLocalPreview(query)
  }
}
