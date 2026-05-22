import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EmailCommandCenter } from '../pages/EmailCommandCenter'

const navigate = vi.fn()

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

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

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
      suggested_labels: ['Fikiri/business_lead'],
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

  it('renders Organize with queue cards, trust copy, and calm row copy', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    expect(screen.getByRole('main', { name: 'Inbox Organize' })).toBeInTheDocument()
    expect(screen.getByText(/Fikiri organizes your inbox/i)).toBeInTheDocument()
    expect(screen.getByText(/Nothing leaves Gmail without your approval/i)).toBeInTheDocument()
    expect(screen.queryByText(/Lead 72/)).not.toBeInTheDocument()
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument()
    expect(screen.getByText('Strong lead')).toBeInTheDocument()
  })

  it('shows Open and Save lead on Opportunities', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Open$/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /^Save lead$/i })).toBeInTheDocument()
  })

  it('navigates to Read when Open is used', async () => {
    renderOrganize()
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /Select Florida Atlantic/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Open$/i }))
    expect(navigate).toHaveBeenCalledWith('/inbox', { state: { openEmailId: 'msg-1' } })
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

    const undoCall = addToast.mock.calls.find((c) => c[0]?.undo?.label === 'Undo')
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
              cleanup_action: 'archive',
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

  it('shows guarded spam and trash actions on Clear out', async () => {
    getEmailTriage.mockResolvedValue({
      emails: [
        {
          ...sampleEmails.emails[0],
          id: 'msg-spam',
          category: 'spam_risk',
          cleanup_action: 'spam_candidate',
        },
      ],
      category_counts: { spam_risk: 1 },
    })

    renderOrganize()
    fireEvent.click(screen.getByRole('tab', { name: /Clear out/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Report spam$/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /^Move to trash$/i })).toBeInTheDocument()
    })
  })

  it('applies recommendations with confirm_destructive for spam', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    getEmailTriage.mockResolvedValue({
      emails: [
        {
          ...sampleEmails.emails[0],
          id: 'msg-spam',
          category: 'spam_risk',
          cleanup_action: 'spam_candidate',
        },
      ],
      category_counts: { spam_risk: 1 },
    })

    renderOrganize()
    fireEvent.click(screen.getByRole('tab', { name: /Clear out/i }))
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })

    fireEvent.click(document.getElementById('email-organize-select-msg-spam')!)
    fireEvent.click(screen.getByRole('button', { name: /Apply recommendations \(1\)/i }))

    await waitFor(() => {
      expect(emailTriageBulkAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'spam_candidate',
          email_ids: ['msg-spam'],
          confirm_destructive: true,
        })
      )
    })
    confirmSpy.mockRestore()
  })

  it('sanitizes jargon in Why panel', async () => {
    const unsureRow = {
      ...sampleEmails.emails[0],
      category: 'review_needed',
      reason: 'Heuristic classification (AI unavailable).',
    }
    getEmailTriage.mockImplementation((params: { category?: string; limit?: number }) => {
      if (params?.category === 'review_needed') {
        return Promise.resolve({
          emails: [unsureRow],
          category_counts: { review_needed: 1 },
        })
      }
      return Promise.resolve({
        emails: [],
        category_counts: { review_needed: 1, business_lead: 0 },
      })
    })

    renderOrganize()
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Not sure/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('tab', { name: /Not sure/i }))
    await waitFor(() => {
      expect(screen.getByText(/Florida Atlantic University inquiry/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /^Why\?$/i }))
    expect(screen.queryByText(/Heuristic classification/i)).not.toBeInTheDocument()
    expect(
      screen.getByText('We were not sure, so we kept it for review.')
    ).toBeInTheDocument()
  })
})
