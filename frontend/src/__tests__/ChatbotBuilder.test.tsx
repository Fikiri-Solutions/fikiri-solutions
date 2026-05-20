import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ChatbotBuilder } from '../pages/ChatbotBuilder'

const { apiClientMock, runPreviewMock, addToastMock } = vi.hoisted(() => ({
  apiClientMock: {
    processDocument: vi.fn(),
    addFaq: vi.fn(),
    addKnowledgeDocument: vi.fn(),
    vectorizeKnowledge: vi.fn(),
    getFaqStats: vi.fn(),
    getFaqCategories: vi.fn(),
    previewChatbotQuery: vi.fn(),
  },
  runPreviewMock: vi.fn(),
  addToastMock: vi.fn(),
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

vi.mock('../pages/chatbotBuilderPreview', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../pages/chatbotBuilderPreview')>()
  return {
    ...actual,
    runChatbotBuilderPreview: runPreviewMock,
  }
})

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: addToastMock }),
}))

const renderBuilder = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ChatbotBuilder />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('ChatbotBuilder preview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClientMock.getFaqStats.mockResolvedValue({ total_faqs: 2, helpful_votes: 1 })
    apiClientMock.getFaqCategories.mockResolvedValue(['general'])
    runPreviewMock.mockResolvedValue({
      botPreview: {
        answer: 'Production preview answer',
        confidence: 0.91,
        source: 'production',
        fallbackUsed: false,
        sources: [{ type: 'faq', id: 'f1', question: 'Hours?' }],
      },
      searchResults: [],
    })
  })

  it('calls runChatbotBuilderPreview with a generated conversation_id on first preview', async () => {
    const user = userEvent.setup()
    renderBuilder()

    const input = screen.getByPlaceholderText('Ask a question')
    await user.type(input, 'What are your hours?')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => {
      expect(runPreviewMock).toHaveBeenCalledTimes(1)
      const [, conversationId] = runPreviewMock.mock.calls[0]
      expect(conversationId).toEqual(expect.any(String))
      expect(String(conversationId).length).toBeGreaterThan(8)
    })
  })

  it('reuses the same conversation_id on follow-up preview turns', async () => {
    const user = userEvent.setup()
    renderBuilder()

    const input = screen.getByPlaceholderText('Ask a question')
    await user.type(input, 'What are your hours?')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => expect(runPreviewMock).toHaveBeenCalledTimes(1))
    const firstConversationId = runPreviewMock.mock.calls[0][1]

    await user.clear(input)
    await user.type(input, 'Do you offer refunds?')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => expect(runPreviewMock).toHaveBeenCalledTimes(2))
    expect(runPreviewMock.mock.calls[1][1]).toBe(firstConversationId)
  })

  it('clear preview resets conversation_id for the next turn', async () => {
    const user = userEvent.setup()
    renderBuilder()

    const input = screen.getByPlaceholderText('Ask a question')
    await user.type(input, 'What are your hours?')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => expect(runPreviewMock).toHaveBeenCalledTimes(1))
    const firstConversationId = runPreviewMock.mock.calls[0][1]

    await user.click(screen.getByRole('button', { name: 'Clear preview' }))

    await user.type(input, 'New thread question')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => expect(runPreviewMock).toHaveBeenCalledTimes(2))
    const secondConversationId = runPreviewMock.mock.calls[1][1]
    expect(secondConversationId).toEqual(expect.any(String))
    expect(secondConversationId).not.toBe(firstConversationId)
  })

  it('displays preview answer and confidence from production path', async () => {
    const user = userEvent.setup()
    renderBuilder()

    await user.type(screen.getByPlaceholderText('Ask a question'), 'hours?')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    expect(await screen.findByText('Production preview answer')).toBeInTheDocument()
    expect(screen.getByText(/91%/)).toBeInTheDocument()
    expect(screen.getByText(/Sources used/)).toBeInTheDocument()
  })

  it('displays fallback production preview without crashing', async () => {
    runPreviewMock.mockResolvedValueOnce({
      botPreview: {
        answer: 'I may be missing some context.',
        confidence: 0.2,
        source: 'production',
        fallbackUsed: true,
        sources: [],
      },
      searchResults: [],
    })

    const user = userEvent.setup()
    renderBuilder()

    await user.type(screen.getByPlaceholderText('Ask a question'), 'unknown')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    expect(await screen.findByText(/Production preview · fallback/)).toBeInTheDocument()
    expect(screen.getByText('I may be missing some context.')).toBeInTheDocument()
  })

  it('shows error toast when preview helper throws', async () => {
    runPreviewMock.mockRejectedValueOnce(new Error('unexpected'))

    const user = userEvent.setup()
    renderBuilder()

    await user.type(screen.getByPlaceholderText('Ask a question'), 'fail')
    await user.click(screen.getByRole('button', { name: 'Test reply' }))

    await waitFor(() => {
      expect(addToastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          title: 'Preview Failed',
        })
      )
    })
  })

  it('FAQ save still calls addFaq', async () => {
    apiClientMock.addFaq.mockResolvedValue({ success: true })
    const user = userEvent.setup()
    renderBuilder()

    await user.type(screen.getByPlaceholderText('Question'), 'Refund policy?')
    await user.type(screen.getByPlaceholderText('Answer'), '30-day refunds.')
    await user.click(screen.getByRole('button', { name: 'Save FAQ' }))

    await waitFor(() => {
      expect(apiClientMock.addFaq).toHaveBeenCalled()
      expect(apiClientMock.addFaq.mock.calls[0][0]).toEqual(
        expect.objectContaining({
          question: 'Refund policy?',
          answer: '30-day refunds.',
        })
      )
    })
  })
})
