import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { Automations } from '../pages/Automations'

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
    getAutomationRules: vi.fn(),
    getAutomationSafetyStatus: vi.fn(),
    getAutomationSuggestions: vi.fn(),
    getAutomationCapabilities: vi.fn(),
    getAutomationMetrics: vi.fn(),
    getAutomationLogs: vi.fn(),
    createAutomationRule: vi.fn(),
    updateAutomationRule: vi.fn(),
    runAutomationPreset: vi.fn(),
  },
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, email: 'test@example.com' } }),
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

vi.mock('../components/AutomationWizard', () => ({
  AutomationWizard: () => <div data-testid="automation-wizard" />,
}))

vi.mock('../components/WebhookPayloadBuilder', () => ({
  WebhookPayloadBuilder: () => <div data-testid="webhook-payload-builder" />,
}))

const renderWithQuery = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('Automations page', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiClientMock.getAutomationRules.mockResolvedValue([
      {
        id: 41,
        name: 'Send Leads to Your Tools',
        description: 'Webhook sync',
        trigger_type: 'email_received',
        action_type: 'trigger_webhook',
        action_parameters: {
          slug: 'email_sheets',
          webhook_url: 'https://example.com/webhook',
        },
        status: 'active',
      },
    ])
    apiClientMock.getAutomationSafetyStatus.mockResolvedValue({
      automation_enabled: true,
      safety_level: 'normal',
      restrictions: [],
    })
    apiClientMock.getAutomationSuggestions.mockResolvedValue([
      { name: 'Auto-qualify urgent leads', description: 'Use keyword-based prioritization' },
    ])
    apiClientMock.getAutomationCapabilities.mockResolvedValue([
      { action_type: 'update_crm_field', capability: 'implemented' },
      { action_type: 'send_notification', capability: 'partial' },
      { action_type: 'trigger_webhook', capability: 'implemented' },
      { action_type: 'schedule_follow_up', capability: 'implemented' },
    ])
    apiClientMock.getAutomationMetrics.mockResolvedValue({
      queued: 2,
      running: 1,
      success: 12,
      failed: 1,
      success_rate_24h: 0.92,
      p95_duration_seconds: 4,
    })
    apiClientMock.getAutomationLogs.mockResolvedValue([
      {
        execution_id: 501,
        rule_id: 41,
        rule_name: 'Send Leads to Your Tools',
        slug: 'email_sheets',
        status: 'success',
        action_result: { message: 'Webhook delivered', summary: 'Delivered' },
        executed_at: new Date().toISOString(),
      },
    ])
  })

  it('renders automations dashboard with queue health and capability badges', async () => {
    renderWithQuery(<Automations />)

    expect(await screen.findByRole('heading', { name: 'Workflow Automations' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Gmail → CRM' })).toBeInTheDocument()
    expect(await screen.findByText(/Q: 2 · R: 1 · ✓ 12 · ✗ 1/)).toBeInTheDocument()
    expect(await screen.findByText(/92% success/)).toBeInTheDocument()
    expect(await screen.findByText('Partial (depends on configuration)')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Recent executions' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Suggested automations' })).toBeInTheDocument()
  })
})
