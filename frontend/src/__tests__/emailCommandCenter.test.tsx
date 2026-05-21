import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EmailCommandCenter } from '../pages/EmailCommandCenter'

const {
  getEmailTriage,
  emailTriageBulkAction,
  getEmailSyncStatus,
  triggerGmailSync,
  classifyEmailTriageUnclassified,
} = vi.hoisted(() => ({
  getEmailTriage: vi.fn(),
  emailTriageBulkAction: vi.fn(),
  getEmailSyncStatus: vi.fn(),
  triggerGmailSync: vi.fn(),
  classifyEmailTriageUnclassified: vi.fn(),
}))

const addToast = vi.fn()

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 108 } }),
}))

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getEmailTriage,
    emailTriageBulkAction,
    getEmailSyncStatus,
    triggerGmailSync,
    classifyEmailTriageUnclassified,
  },
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast }),
}))

function renderOrganize(initialPath = '/inbox/command-center') {
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
  category_counts: { business_lead: 1, action_needed: 0, review_needed: 0 },
  pagination: { total_count: 1, has_more: false },
}

describe('EmailCommandCenter (Organize)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEmailTriage.mockResolvedValue(sampleEmails)
    getEmailSyncStatus.mockResolvedValue({
      syncing: false,
      total_emails: 5,
      sync_status: 'completed',
    })
    emailTriageBulkAction.mockResolvedValue({ processed: 1 })
    triggerGmailSync.mockResolvedValue({ message: 'ok' })
    classifyEmailTriageUnclassified.mockResolvedValue({ count: 0, classified: [] })
  })

  it('renders Organize with queue cards and calm row copy', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    expect(screen.getByRole('main', { name: 'Inbox Organize' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Opportunities/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Update & sort/i })).toBeInTheDocument()
    expect(screen.queryByText(/Lead 72/)).not.toBeInTheDocument()
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument()
    expect(screen.getByText('Strong lead')).toBeInTheDocument()
  })

  it('switches to Needs reply queue and refetches', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    getEmailTriage.mockResolvedValueOnce({ emails: [], category_counts: sampleEmails.category_counts })
    fireEvent.click(screen.getByRole('tab', { name: /Needs reply/i }))

    await waitFor(() => {
      expect(getEmailTriage).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'action_needed' })
      )
    })
  })

  it('selects rows and enables Save lead action', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /Select Florida Atlantic/i }))
    expect(screen.getByRole('button', { name: /Save lead \(1\)/i })).toBeEnabled()
  })

  it('does not expose delete or spam bulk actions in simple mode', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    expect(screen.queryByLabelText('Bulk action')).not.toBeInTheDocument()
    expect(screen.queryByText(/Delete/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/spam/i)).not.toBeInTheDocument()
  })

  it('calls dismiss immediately and offers undo that restores to queue', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('checkbox', { name: /Select Florida Atlantic/i }))
    fireEvent.click(screen.getByRole('button', { name: /Mark done \(1\)/i }))

    await waitFor(() => {
      expect(emailTriageBulkAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'dismiss',
          email_ids: ['msg-1'],
        })
      )
    })
    expect(addToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: expect.stringMatching(/Marked 1 as done/i),
        undo: expect.objectContaining({ label: 'Undo' }),
      })
    )

    const undoCall = addToast.mock.calls.find(
      (c) => c[0]?.undo?.label === 'Undo'
    )
    undoCall?.[0]?.undo?.onClick()
    await waitFor(() => {
      expect(emailTriageBulkAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'restore_to_queue',
          email_ids: ['msg-1'],
        })
      )
    })
  })

  it('confirms before File away in Gmail on Clear out queue', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const clearOutCategories = new Set([
      'newsletter_marketing',
      'personal_non_business',
      'spam_risk',
      'vendor_partner',
    ])
    getEmailTriage.mockImplementation((params: { category?: string }) => {
      if (params?.category && clearOutCategories.has(params.category)) {
        return Promise.resolve({
          emails: [
            {
              ...sampleEmails.emails[0],
              id: 'msg-2',
              category: 'newsletter_marketing',
            },
          ],
          category_counts: { newsletter_marketing: 1, business_lead: 1 },
        })
      }
      return Promise.resolve(sampleEmails)
    })

    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('tab', { name: /Clear out/i }))
    await waitFor(() => {
      expect(getEmailTriage).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'newsletter_marketing' })
      )
    })

    const rowCheckbox = document.getElementById('email-organize-select-msg-2')
    expect(rowCheckbox).toBeTruthy()
    fireEvent.click(rowCheckbox!)
    fireEvent.click(screen.getByRole('button', { name: /File away in Gmail \(1\)/i }))

    expect(confirmSpy).toHaveBeenCalled()
    expect(emailTriageBulkAction).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })
})
