import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { GettingStartedWizard } from '../components/GettingStartedWizard'

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
    getGmailConnectionStatus: vi.fn(),
    getLeads: vi.fn(),
    getDashboardTimeseries: vi.fn(),
    getAutomationRules: vi.fn(),
  },
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, email: 'test@example.com' } }),
}))

describe('GettingStartedWizard business health check', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiClientMock.getGmailConnectionStatus.mockResolvedValue({ connected: true })
    apiClientMock.getLeads.mockResolvedValue([])
    apiClientMock.getDashboardTimeseries.mockResolvedValue({
      data: {
        timeseries: [
          { date: '2025-01-01', emails: 0 },
        ],
      },
    })
    apiClientMock.getAutomationRules.mockResolvedValue([])
  })

  const renderWizard = () =>
    render(
      <MemoryRouter>
        <GettingStartedWizard />
      </MemoryRouter>
    )

  it('shows dynamic business health results based on backend data', async () => {
    renderWizard()

    // Move from the welcome step to the health check step
    fireEvent.click(
      screen.getByRole('button', { name: /Start Your Business Health Check/i })
    )

    await waitFor(() => {
      expect(
        screen.getByText('Your Business Health Check')
      ).toBeInTheDocument()
    })

    expect(screen.getAllByText('Lead Management').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Score: 0/100').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Email Automation').length).toBeGreaterThan(0)
    expect(screen.getAllByText('critical').length).toBeGreaterThan(0)

    expect(
      screen.getAllByText('Connect your email to automatically capture leads').length
    ).toBeGreaterThan(0)
    expect(
      screen.getAllByText('No leads in your CRM').length
    ).toBeGreaterThan(0)
  })
})

