import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EmailCommandCenter } from '../pages/EmailCommandCenter'

const {
  getEmailTriage,
  emailTriageBulkAction,
  classifyEmailTriage,
  getEmailSyncStatus,
  triggerGmailSync,
  classifyEmailTriageUnclassified,
} = vi.hoisted(() => ({
  getEmailTriage: vi.fn(),
  emailTriageBulkAction: vi.fn(),
  classifyEmailTriage: vi.fn(),
  getEmailSyncStatus: vi.fn(),
  triggerGmailSync: vi.fn(),
  classifyEmailTriageUnclassified: vi.fn(),
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 108 } }),
}))

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getEmailTriage,
    emailTriageBulkAction,
    classifyEmailTriage,
    getEmailSyncStatus,
    triggerGmailSync,
    classifyEmailTriageUnclassified,
  },
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

function renderCenter(initialPath = '/inbox/command-center') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/inbox/command-center" element={<EmailCommandCenter />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const sampleEmails = {
  emails: [
    {
      id: 'msg-1',
      from: 'noreply@fau.edu',
      subject: 'Florida Atlantic University inquiry',
      category: 'business_lead',
      lead_score: 72,
      urgency_score: 40,
      cleanup_action: 'keep',
      confidence: 0.88,
      reason: 'Pricing inquiry',
    },
  ],
  pagination: { total_count: 1, has_more: false },
}

describe('EmailCommandCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEmailTriage.mockResolvedValue(sampleEmails)
    getEmailSyncStatus.mockResolvedValue({
      syncing: false,
      total_emails: 5,
      sync_status: 'completed',
    })
    emailTriageBulkAction.mockResolvedValue({ processed: 1 })
    classifyEmailTriage.mockResolvedValue({ count: 1, classified: [] })
    triggerGmailSync.mockResolvedValue({ message: 'ok' })
    classifyEmailTriageUnclassified.mockResolvedValue({ count: 0, classified: [] })
  })

  it('switches tabs and refetches with new category', async () => {
    renderCenter()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    expect(getEmailTriage).toHaveBeenCalledWith(
      expect.objectContaining({ category: 'business_lead' })
    )

    getEmailTriage.mockResolvedValueOnce({ emails: [], pagination: { total_count: 0 } })
    fireEvent.click(screen.getByRole('tab', { name: 'Action Needed' }))

    await waitFor(() => {
      expect(getEmailTriage).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'action_needed' })
      )
    })
  })

  it('selects emails via checkbox', async () => {
    renderCenter()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    const checkbox = screen.getByRole('checkbox', {
      name: /Select Florida Atlantic University inquiry/i,
    })
    fireEvent.click(checkbox)
    expect(screen.getByRole('button', { name: /Apply \(1\)/i })).toBeEnabled()
  })

  it('requires confirmation before destructive bulk action', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderCenter()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('checkbox', { name: /Select Florida Atlantic/i }))
    fireEvent.change(screen.getByLabelText('Bulk action'), {
      target: { value: 'delete_candidate' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Apply \(1\)/i }))

    expect(confirmSpy).toHaveBeenCalled()
    expect(emailTriageBulkAction).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('calls bulk API with confirm_destructive when user confirms spam', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderCenter()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('checkbox', { name: /Select Florida Atlantic/i }))
    fireEvent.change(screen.getByLabelText('Bulk action'), {
      target: { value: 'spam_candidate' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Apply \(1\)/i }))

    await waitFor(() => {
      expect(emailTriageBulkAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'spam_candidate',
          confirm_destructive: true,
          email_ids: ['msg-1'],
        })
      )
    })
    confirmSpy.mockRestore()
  })
})
