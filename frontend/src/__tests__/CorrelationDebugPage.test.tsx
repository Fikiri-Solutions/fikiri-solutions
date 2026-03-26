import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CorrelationDebugPage } from '../pages/CorrelationDebugPage'

const { getCorrelationTraceMock } = vi.hoisted(() => ({
  getCorrelationTraceMock: vi.fn()
}))

vi.mock('../services/apiClient', () => ({
  apiClient: { getCorrelationTrace: getCorrelationTraceMock }
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: vi.fn() })
}))

describe('CorrelationDebugPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('loads trace on button click and shows timeline', async () => {
    const user = userEvent.setup()
    getCorrelationTraceMock.mockResolvedValue({
      correlation_id: 'abc',
      user_id: 1,
      limits: { per_section: 50 },
      sections: {
        crm_events: [
          { created_at: '2025-02-01T12:00:00', event_type: 'lead_created', source: 'api' }
        ]
      }
    })

    render(
      <MemoryRouter>
        <CorrelationDebugPage />
      </MemoryRouter>
    )

    await user.type(screen.getByPlaceholderText(/Paste UUID/i), 'abc')
    await user.click(screen.getByRole('button', { name: /Load trace/i }))

    expect(getCorrelationTraceMock).toHaveBeenCalledWith('abc')
    expect(await screen.findByText(/Timeline/i)).toBeInTheDocument()
    expect(screen.getByText('lead_created')).toBeInTheDocument()
  })

  it('shows friendly message when trace endpoint is disabled', async () => {
    const user = userEvent.setup()
    getCorrelationTraceMock.mockRejectedValue({
      response: { status: 404, data: { error: 'Correlation trace disabled', code: 'TRACE_DISABLED' } }
    })

    render(
      <MemoryRouter>
        <CorrelationDebugPage />
      </MemoryRouter>
    )

    await user.type(screen.getByPlaceholderText(/Paste UUID/i), 'x')
    await user.click(screen.getByRole('button', { name: /Load trace/i }))

    expect(await screen.findByText(/Correlation trace unavailable/i)).toBeInTheDocument()
  })
})
