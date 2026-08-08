import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AdminSiteChat } from '../pages/admin/AdminSiteChat'
import { apiClient } from '../services/apiClient'

vi.mock('../services/apiClient', () => ({
  apiClient: {
    listSiteChatSessions: vi.fn(),
    getSiteChatSession: vi.fn(),
    exportSiteChatSession: vi.fn(),
  },
}))

describe('AdminSiteChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.listSiteChatSessions).mockResolvedValue({
      sessions: [
        {
          session_id: 'site_demo_1',
          turn_count: 3,
          last_mode: 'contact',
          latest_lead_tier: 'possible',
          latest_lead_synopsis: 'Visitor asked about pricing',
          last_seen_at: '2026-08-06T12:00:00Z',
        },
      ],
      total: 1,
      limit: 25,
      offset: 0,
    })
    vi.mocked(apiClient.getSiteChatSession).mockResolvedValue({
      session: {
        session_id: 'site_demo_1',
        first_seen_at: '2026-08-06T11:00:00Z',
        last_seen_at: '2026-08-06T12:00:00Z',
        source_page: '/',
        latest_handoff_path: '/contact',
      },
      messages: [
        { role: 'user', content: 'How much does it cost?' },
        { role: 'assistant', content: 'Pricing depends on your plan.', mode: 'contact' },
      ],
    })
  })

  it('lists sessions and opens a transcript', async () => {
    const user = userEvent.setup()
    render(<AdminSiteChat />)

    await waitFor(() => {
      expect(screen.getByText('site_demo_1')).toBeInTheDocument()
    })

    await user.click(screen.getByText('site_demo_1'))

    await waitFor(() => {
      expect(screen.getByText('How much does it cost?')).toBeInTheDocument()
      expect(screen.getByText('Pricing depends on your plan.')).toBeInTheDocument()
    })
    expect(apiClient.getSiteChatSession).toHaveBeenCalledWith('site_demo_1')
    expect(screen.getByRole('button', { name: /Download \.txt/i })).toBeInTheDocument()
  })

  it('reloads the open transcript when Refresh is clicked', async () => {
    const user = userEvent.setup()
    render(<AdminSiteChat />)

    await waitFor(() => expect(screen.getByText('site_demo_1')).toBeInTheDocument())
    await user.click(screen.getByText('site_demo_1'))
    await waitFor(() => expect(screen.getByText('How much does it cost?')).toBeInTheDocument())

    const detailCallsBefore = vi.mocked(apiClient.getSiteChatSession).mock.calls.length
    await user.click(screen.getByRole('button', { name: /Refresh/i }))

    await waitFor(() => {
      expect(vi.mocked(apiClient.getSiteChatSession).mock.calls.length).toBeGreaterThan(
        detailCallsBefore
      )
    })
  })
})